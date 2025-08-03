# AGENTS.md

## AI Development Methodology for grepo2

### Overview
Dieses Dokument beschreibt die Methodik und Best Practices für die AI-gestützte Entwicklung von grepo2, einem Git-Repository-Management-Tool mit GitHub-Integration.

### Entwicklungsphilosophie

#### 1. Incremental Development
- **Prinzip**: Entwicklung in kleinen, nachvollziehbaren Schritten
- **Motivation**: Vermeidung von Timeout-Problemen und bessere Nachverfolgbarkeit
- **Implementierung**: Jede größere Änderung wird in 10-15 kleine Schritte aufgeteilt

#### 2. Version Management
- **Semantic Versioning**: MAJOR.MINOR.PATCH.HOTFIX
- **Regression Handling**: Bei Verhaltensänderungen werden Patch-Versionen erstellt
- **Feature Preservation**: Neue Versionen behalten alle bestehenden Features

#### 3. Documentation-First Approach
- **CHANGELOG.md**: Umfassende Dokumentation aller Änderungen
- **Code Comments**: Ausführliche Kommentierung komplexer Funktionen
- **User Experience**: Fokus auf intuitive Bedienung

### AI Assistant Workflows

#### Code Analysis Workflow
1. **Context Gathering**: Sammeln von relevanten Dateien und Struktur-Informationen
2. **Pattern Recognition**: Identifikation von Code-Mustern und -Strukturen
3. **Impact Assessment**: Bewertung der Auswirkungen geplanter Änderungen
4. **Implementation Planning**: Aufteilung in ausführbare Schritte

#### Bug Fix Workflow
1. **Issue Identification**: Präzise Beschreibung des Problems
2. **Root Cause Analysis**: Vergleich mit vorherigen funktionierenden Versionen
3. **Solution Design**: Entwicklung einer minimalen, zielgerichteten Lösung
4. **Regression Testing**: Sicherstellung, dass bestehende Features erhalten bleiben

#### Feature Development Workflow
1. **Requirements Analysis**: Verständnis der Benutzerwünsche
2. **Architecture Integration**: Einbindung in bestehende Struktur
3. **Progressive Implementation**: Schrittweise Umsetzung mit Zwischentests
4. **Documentation Update**: Aktualisierung aller relevanten Dokumentationen

### Technical Standards

#### Code Quality
- **Python Best Practices**: PEP 8 Konformität, Type Hints wo sinnvoll
- **Error Handling**: Umfassende Try-Catch-Blöcke mit benutzerfreundlichen Meldungen
- **User Feedback**: Visuelle Indikatoren für alle längeren Operationen

#### Architecture Principles
- **Modularity**: Klare Trennung von GitHub API, Git CLI und UI-Komponenten
- **Configuration Management**: Zentrale Konfigurationsverwaltung
- **Extensibility**: Einfache Erweiterbarkeit für neue Features

#### Testing Approach
- **Manual Testing**: Systematische Tests aller Kernfunktionen
- **Edge Case Handling**: Besondere Aufmerksamkeit für Randfälle
- **User Journey Testing**: Tests aus Benutzersicht

### Version History Insights

#### Version 3.7.1 → 3.7.3
- **Major Addition**: Automatisches Issue-Closing bei Commit-Integration
- **Enhancement**: CHANGELOG.md Integration für bessere Dokumentation
- **Architecture**: Erweiterte GitHub API Integration

#### Version 3.7.3 → 3.7.3.1
- **Regression Fix**: Wiederherstellung des ursprünglichen Startup-Verhaltens
- **Issue**: TUI startete nicht mehr standardmäßig
- **Solution**: Wiederherstellung der "grepo2" → TUI, "grepo2 go" → CLI Logik

#### Version 3.7.3.1 → 3.7.3.2
- **TUI Navigation Restoration**: Vollständige Wiederherstellung der Repository-Auswahl im Hauptmenü
- **Issue**: Vereinfachte TUI ohne Repository-Navigation und -Management
- **Solution**: Integration der kompletten Menüführung aus v3.7.2 mit modernem Look & Feel
- **Feature Preservation**: Alle v3.7.3+ Features (Auto-Close, CHANGELOG, AI-Integration) beibehalten

### AI Development Challenges

#### Challenge 1: Context Limits
- **Problem**: Große Dateien können nicht in einem Zug verarbeitet werden
- **Solution**: Incremental development approach mit targeted file reading
- **Learning**: Strukturierte Herangehensweise ist effizienter als große Änderungen

#### Challenge 2: Regression Prevention
- **Problem**: Neue Features können bestehende Funktionalität beeinträchtigen
- **Solution**: Systematischer Vergleich mit vorherigen Versionen
- **Learning**: Verhaltensänderungen müssen explizit dokumentiert und begründet werden

#### Challenge 3: User Experience Consistency
- **Problem**: Technische Verbesserungen dürfen Benutzererfahrung nicht verschlechtern
- **Solution**: Beibehaltung gewohnter Workflows bei gleichzeitiger Feature-Erweiterung
- **Learning**: Backwards Compatibility ist entscheidend für Benutzerakzeptanz

#### Challenge 4: TUI Navigation Regression
- **Problem**: Vereinfachte TUI-Implementierung entfernte Repository-Auswahl aus Hauptmenü
- **Solution**: Systematische Wiederherstellung der v3.7.2 Menüstruktur mit Beibehaltung neuer Features
- **Learning**: Modernes UI-Design darf nicht auf Kosten der Funktionalität gehen

### Best Practices for AI Assistants

#### Code Reading Strategy
1. **Hierarchical Reading**: Erst Struktur, dann Details
2. **Pattern-Based Analysis**: Suche nach wiederkehrenden Mustern
3. **Targeted Context**: Nur relevante Bereiche einlesen
4. **Parallel Analysis**: Multiple files parallel analysieren wo möglich

#### Development Strategy
1. **Plan Before Code**: Thorough planning prevents later refactoring
2. **Preserve Working State**: Never break existing functionality
3. **Document Everything**: Every change should be traceable
4. **Test Incrementally**: Validate each step before proceeding

#### Communication Strategy
1. **Clear Intent**: Explicitly state what will be changed
2. **Progress Updates**: Regular status updates during long operations
3. **Problem Transparency**: Honest communication about challenges
4. **Solution Explanation**: Explain why specific approaches were chosen

### Future Development Guidelines

#### Scalability Considerations
- **Performance**: Monitor execution times for large repositories
- **Memory Usage**: Efficient handling of large data sets
- **API Limits**: Respect GitHub API rate limits

#### Extensibility Planning
- **Plugin Architecture**: Consider plugin system for custom integrations
- **Configuration Flexibility**: More granular user configuration options
- **Integration Points**: APIs for external tool integration

#### User Experience Evolution
- **UI/UX Improvements**: Continuous refinement of user interface
- **Workflow Optimization**: Streamline common user workflows
- **Accessibility**: Ensure tool is accessible to diverse user groups

### Conclusion

Die AI-gestützte Entwicklung von grepo2 zeigt, dass komplexe Software-Projekte erfolgreich durch strukturierte, incremental Methodik entwickelt werden können. Der Schlüssel liegt in:

1. **Methodischer Herangehensweise**: Kleine Schritte, große Wirkung
2. **Kontinuierlicher Dokumentation**: Jede Änderung wird nachvollziehbar festgehalten
3. **Benutzerzentrierung**: Technische Exzellenz dient der Benutzererfahrung
4. **Adaptivität**: Flexible Anpassung an neue Anforderungen bei Beibehaltung bewährter Strukturen

Diese Prinzipien haben sich als erfolgreich erwiesen und sollten als Grundlage für zukünftige Entwicklungszyklen dienen.

---

**Document Version**: 1.1  
**Last Updated**: 2025-08-03  
**grepo2 Version**: 3.7.3.2  
**Author**: AI Development Assistant  
