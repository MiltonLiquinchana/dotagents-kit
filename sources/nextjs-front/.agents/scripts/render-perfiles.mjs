// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {get,validar} from './stack.mjs';
const args=process.argv.slice(2);
const option=name=>args[args.indexOf(name)+1];
if(!args.includes('--output') || !args.includes('--prefijo-api')) throw new Error('Uso: --output RAIZ --prefijo-api /alias-aprobado');
const output=path.resolve(option('--output'));
const prefix=option('--prefijo-api');
if(!/^\/[a-z0-9-]+$/.test(prefix)) throw new Error('Prefijo API no válido');
const agents=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
validar();
const names=Object.fromEntries(['archivo_seccion_ui','modelo','response','request','repositorio_interfaz','repositorio_implementacion','servicio_interfaz','servicio_implementacion','controlador_implementacion','controlador_interfaz'].map(key=>[key,get('nomenclatura.'+key)]));
const tokens={PREFIJO_API:prefix,SECCION_UI:names.archivo_seccion_ui.replace('{nombre}','perfiles').replace(/\.tsx$/,'')};
for(const [token,key,entity] of [
 ['PerfilModel','modelo','Perfil'],['EstadoPerfilModel','modelo','EstadoPerfil'],
 ['PerfilResponse','response','Perfil'],['EstadoPerfilResponse','response','EstadoPerfil'],
 ['PerfilRequest','request','Perfil'],['PreRegistroRequest','request','PreRegistro'],['FiltroPerfilRequest','request','FiltroPerfil'],
 ['Repositorio','repositorio_interfaz','Perfiles'],['RepositorioImpl','repositorio_implementacion','Perfiles'],
 ['Servicio','servicio_interfaz','Perfiles'],['ServicioImpl','servicio_implementacion','Perfiles'],
 ['Controlador','controlador_implementacion','Perfiles'],['ControladorInterfaz','controlador_interfaz','Perfiles']
]) tokens[token]=names[key].replace('{Entidad}',entity);
const api=path.join(agents,'skills/api-integration-architect/assets/templates/gestion-usuarios');
const ui=path.join(agents,'skills/frontend-developer/assets/templates/gestion-usuarios');
const content=file=>fs.readFileSync(file,'utf8').replace(/^\/\/ generado automáticamente[^\n]*\n/,'');
const catalog=path.join(api,'catalogo-actions.template.ts');
tokens.CATALOGO_ACTIONS=fs.existsSync(catalog) ? '{'+content(catalog)+'}' : '{}';
const files=[
 ['PerfilResponse','domains/responses/'+tokens.PerfilResponse+'.ts',api],
 ['EstadoPerfilResponse','domains/responses/'+tokens.EstadoPerfilResponse+'.ts',api],
 ['PerfilModel','domains/models/'+tokens.PerfilModel+'.ts',api],['EstadoPerfilModel','domains/models/'+tokens.EstadoPerfilModel+'.ts',api],
 ['PerfilRequest','domains/request/'+tokens.PerfilRequest+'.ts',api],['GestionTipos','domains/types/GestionTipos.ts',api],
 ['Repository','repository/'+tokens.Repositorio+'.ts',api],['RepositoryImpl','repository/'+tokens.RepositorioImpl+'.ts',api],
 ['Service','services/'+tokens.Servicio+'.ts',api],['ServiceImpl','services/'+tokens.ServicioImpl+'.ts',api],
 ['ControllerInterface','controllers/'+tokens.ControladorInterfaz+'.ts',api],['Controller','controllers/'+tokens.Controlador+'.ts',api],
 ['GestionProvider','app/ui/perfiles/GestionProvider.tsx',ui],['PerfilForm','app/ui/perfiles/PerfilForm.tsx',ui],
 ['PerfilesSection','app/ui/perfiles/'+tokens.SECCION_UI+'.tsx',ui],['PerfilesPage','app/perfiles/page.tsx',ui],
 ['PreRegistroPage','app/(login)/pre-register/[[...pre-register]]/page.tsx',ui],
];
if(fs.existsSync(path.join(api,'actions.template.ts'))) files.push(['actions','app/perfiles/actions.ts',api]);
if(fs.existsSync(path.join(api,'Perfiles.test.template.ts'))) files.push(['Perfiles.test','__tests__/perfiles.test.ts',api]);
const pending=[];
for(const [base,destination,folder] of files){
 const ext=destination.endsWith('.tsx') ? 'tsx':'ts';
 let text=content(path.join(folder,base+'.template.'+ext));
 text=text.replace(/__(\w+)__/g,(_,key)=>{if(!(key in tokens))throw new Error('Marcador desconocido: '+key);return tokens[key];});
 const target=path.join(output,destination);
 if(fs.existsSync(target))throw new Error('Archivo existente: revisar diff antes de cambiar '+target);
 pending.push([target,text]);
}
for(const [file,text] of pending){fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,text,{flag:'wx'});}
console.log('Perfiles materializados: '+pending.length+' archivos; prefijo aprobado '+prefix);
