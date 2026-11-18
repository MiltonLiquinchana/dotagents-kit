// Conserva strings, elimina comentarios sin confundir URLs o comentarios con plugins.
export function sinComentarios(texto) {
  let salida = '', modo = '', escape = false;
  for (let i = 0; i < texto.length; i++) {
    const c = texto[i], siguiente = texto[i + 1];
    if (modo === 'linea') {
      if (c === '\n') { modo = ''; salida += c; }
    } else if (modo === 'bloque') {
      if (c === '*' && siguiente === '/') { modo = ''; i++; }
      else if (c === '\n') salida += c;
    } else if (modo) {
      salida += c;
      if (escape) escape = false;
      else if (c === '\\') escape = true;
      else if (c === modo) modo = '';
    } else if (c === '/' && siguiente === '/') { modo = 'linea'; i++; }
    else if (c === '/' && siguiente === '*') { modo = 'bloque'; i++; }
    else { salida += c; if (c === '"' || c === "'") modo = c; }
  }
  return salida;
}

// Solo analiza texto; no ejecuta Groovy ni consulta repositorios.
export const literalVersion = value => typeof value === 'string' && /^\d+(?:\.\d+)*(?:[-+][A-Za-z0-9][A-Za-z0-9.-]*)?$/.test(value);
export function quoted(expression) {
  const raw = expression.trim();
  const match = raw.match(/^(['"])([^\r\n]*?)\1$/);
  return match && !match[2].includes(match[1]) && !match[2].includes('\\') ? match[2] : null;
}
function expression(text, start) {
  let quote = '', escape = false, depth = 0, out = '';
  for (let i = start; i < text.length; i++) {
    const c = text[i];
    if (quote) {
      out += c;
      if (escape) escape = false;
      else if (c === '\\') escape = true;
      else if (c === quote) quote = '';
    } else if (c === '"' || c === "'") { quote = c; out += c; }
    else if (c === '(') { depth++; out += c; }
    else if (c === ')') { if (!depth) break; depth--; out += c; }
    else if (!depth && /[\n;{}]/.test(c)) break;
    else out += c;
  }
  return out.trim();
}
function argument(raw) {
  raw = raw.trim();
  if (raw.startsWith('(') && raw.endsWith(')')) raw = raw.slice(1, -1).trim();
  return raw;
}
function depths(text) {
  const result = []; let depth = 0, quote = '', escape = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i]; result.push(depth);
    if (quote) {
      if (escape) escape = false;
      else if (c === '\\') escape = true;
      else if (c === quote) quote = '';
    } else if (c === '"' || c === "'") quote = c;
    else if (c === '{') depth++;
    else if (c === '}') depth--;
  }
  return result;
}
export function analizarGradle(raw, archivo) {
  const text = sinComentarios(raw), ds = depths(text);
  const origen = index => ({archivo, linea: text.slice(0, index).split('\n').length});
  const ext = [...text.matchAll(/\bext\s*\{/g)].filter(m => ds[m.index] === 0).map(m => {
    const open = text.indexOf('{', m.index); let end = open + 1;
    while (end < text.length && !(text[end] === '}' && ds[end] === 1)) end++;
    return [open, end];
  });
  const inExt = index => ext.some(([a,b]) => index > a && index < b && ds[index] === 1);
  const properties = [];
  for (const m of text.matchAll(/(?<![\w.])((?:ext\.)?springCloudVersion)\s*([+*/%-]?=)\s*/g)) {
    const rawValue = expression(text, m.index + m[0].length), value = quoted(rawValue);
    const local = m[2] === '=' && ((m[1].startsWith('ext.') && ds[m.index] === 0) || inExt(m.index));
    properties.push({nombre:'springCloudVersion', expresion:rawValue, version:local && literalVersion(value) ? value : null, estado:local && literalVersion(value) ? 'literal' : 'no_resoluble', origen:origen(m.index)});
  }
  for (const m of text.matchAll(/(?<![\w.])set\s*\(\s*(['"])springCloudVersion\1\s*,\s*/g)) {
    const rawValue = expression(text, m.index + m[0].length), value = quoted(rawValue);
    const end = m.index + m[0].length + rawValue.length;
    const tail = text.slice(end).match(/^\s*\)([^\n;}]*)(?:[\n;}]|$)/);
    const local = (ds[m.index] === 0 || inExt(m.index)) && tail && !tail[1].trim();
    properties.push({nombre:'springCloudVersion', expresion:rawValue, version:local && literalVersion(value) ? value : null, estado:local && literalVersion(value) ? 'literal' : 'no_resoluble', origen:origen(m.index)});
  }
  for (const m of text.matchAll(/(?<![\w.])(?:ext\.)?springCloudVersion\s*(?:\+\+|--)/g)) properties.push({nombre:'springCloudVersion', expresion:m[0], version:null, estado:'no_resoluble', origen:origen(m.index)});
  const plugins = [];
  for (const m of text.matchAll(/\bid\s*(?:\(\s*(['"])([^'"\n]+)\1\s*\)|(['"])([^'"\n]+)\3)\s+version\s*/g)) {
    let rawValue = expression(text, m.index + m[0].length);
    rawValue = rawValue.replace(/\s+apply\s+(?:false|true)\s*$/, '');
    const value = quoted(argument(rawValue));
    plugins.push({id:m[2] || m[4], version:literalVersion(value) ? value : null, estado:literalVersion(value) ? 'literal' : 'no_resoluble', expresion:rawValue, origen:origen(m.index)});
  }
  const boms = [], dependencies = [];
  function coordinate(rawValue, m, kind) {
    const value = quoted(argument(rawValue));
    const parts = value?.match(/^([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+)(?::(.+))?$/);
    const prefix = argument(rawValue).match(/^['"]([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+):/);
    const item = {coordenada:parts ? parts[1]+':'+parts[2] : prefix ? prefix[1]+':'+prefix[2] : null, version:null, estado:'no_resoluble', expresion:rawValue, origen:origen(m.index)};
    if (parts && !parts[3] && kind === 'dependencia') item.estado='del_bom';
    else if (parts && literalVersion(parts[3])) { item.version=parts[3]; item.estado='literal'; }
    else if (kind === 'bom' && parts?.[3] === '${springCloudVersion}' && argument(rawValue).startsWith('"') && properties.length === 1 && properties[0].estado === 'literal') {
      item.version=properties[0].version; item.estado='literal'; item.procedencia='propiedad_local'; item.propiedad_referenciada='springCloudVersion'; item.origen_propiedad=properties[0].origen;
    }
    return item;
  }
  for (const m of text.matchAll(/\bmavenBom\s*/g)) boms.push(coordinate(expression(text,m.index+m[0].length),m,'bom'));
  for (const m of text.matchAll(/\b(implementation|api|compileOnly|runtimeOnly|annotationProcessor|testImplementation|testRuntimeOnly|testCompileOnly|testAnnotationProcessor|developmentOnly)\b\s*(?=['"(A-Za-z_$])/g)) {
    const rawValue=expression(text,m.index+m[0].length), arg=argument(rawValue);
    const platform=arg.match(/^(?:platform|enforcedPlatform)\s*\((.*)\)$/s);
    const item=coordinate(platform ? platform[1] : rawValue,m,platform ? 'bom' : 'dependencia');
    item.configuraciones=[m[1]];
    (platform ? boms : dependencies).push(item);
  }
  const javaMatches = [...text.matchAll(/\bJavaLanguageVersion\.of\s*\(([^)]+)\)/g)];
  const j = javaMatches.length === 1 ? javaMatches[0] : null;
  const java = {version:j && /^\d+$/.test(j[1].trim()) ? j[1].trim() : null, estado:j && /^\d+$/.test(j[1].trim()) ? 'literal':'no_resoluble', origen:j ? origen(j.index):{archivo}};
  return {java, plugins, dependencias:dependencies, boms, propiedades_version:properties};
}
