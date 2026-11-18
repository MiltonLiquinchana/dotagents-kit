// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.repository;
import java.sql.*;
import java.util.*;
import org.springframework.stereotype.Repository;
import org.springframework.dao.DataIntegrityViolationException;
// si backend.persistencia=jpa
import jakarta.persistence.EntityManager;
import org.hibernate.Session;
// si backend.persistencia=jdbc
import javax.sql.DataSource;
import org.springframework.jdbc.datasource.DataSourceUtils;
// fin

/** Solo procedimientos aprobados; sin publicación de CRUD Data REST. */
@Repository
public class PerfilesRepositoryImpl implements PerfilesRepository {
// si backend.persistencia=jpa
    private final EntityManager manager;
    public PerfilesRepositoryImpl(EntityManager manager) { this.manager=manager; }
    @Override public List<Map<String,Object>> call(String procedure, Object... arguments) {
        return manager.unwrap(Session.class).doReturningWork(c -> execute(c, procedure, arguments));
    }
// si backend.persistencia=jdbc
    private final DataSource source;
    public PerfilesRepositoryImpl(DataSource source) { this.source=source; }
    @Override public List<Map<String,Object>> call(String procedure, Object... arguments) {
        Connection connection=DataSourceUtils.getConnection(source);
        try { return execute(connection, procedure, arguments); }
        catch (SQLException ex) { throw new DataIntegrityViolationException("Conflicto de persistencia", ex); }
        finally { DataSourceUtils.releaseConnection(connection, source); }
    }
// fin
    private List<Map<String,Object>> execute(Connection connection, String procedure, Object[] arguments) throws SQLException {
        // WHY: los nombres provienen del contrato, nunca de parámetros HTTP.
        if (!procedure.matches("[A-Za-z_][A-Za-z0-9_]*")) throw new IllegalArgumentException("Procedimiento inválido");
        String parameters=String.join(",", Collections.nCopies(arguments.length,"?"));
        try (CallableStatement query=connection.prepareCall("{call "+procedure+"("+parameters+")}")) {
            for (int i=0; i<arguments.length; i++) query.setObject(i+1,arguments[i]);
            boolean rows=query.execute();
            List<Map<String,Object>> result=new ArrayList<>();
            while (true) {
                if (rows) {
                    try (ResultSet rs=query.getResultSet()) {
                        ResultSetMetaData meta=rs.getMetaData();
                        while (rs.next()) {
                            Map<String,Object> row=new LinkedHashMap<>();
                            for (int i=1;i<=meta.getColumnCount();i++) row.put(meta.getColumnLabel(i),rs.getObject(i));
                            result.add(row);
                        }
                    }
                } else if (query.getUpdateCount()==-1) break;
                rows=query.getMoreResults();
            }
            return result;
        }
    }
}
