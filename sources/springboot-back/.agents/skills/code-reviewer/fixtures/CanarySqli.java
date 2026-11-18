// Canario del Paso 0 (ver .agents/skills/code-reviewer/references/sonarqube-gate.md). NO es código del proyecto.
// Sin 'package' a propósito: el análisis de un fichero suelto no tiene ruta y Sonar
// reportaría java:S1598 (artefacto). Se espera que aparezca java:S2077 (SQL dinámico).
// Debe vivir fuera de <servicio>/src/: touched-files.sh y el CI no lo analizan.
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

public class CanarySqli {

    public boolean exists(Connection connection, String userInput) throws SQLException {
        String query = "SELECT id FROM users WHERE name = '" + userInput + "'";
        try (Statement statement = connection.createStatement();
             ResultSet resultSet = statement.executeQuery(query)) {
            return resultSet.next();
        }
    }
}
