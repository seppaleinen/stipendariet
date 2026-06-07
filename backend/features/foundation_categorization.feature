Feature: Foundation Categorization and Admin Functionality

  Background: 
    Given the application is running with database connection
    And the foundation data is loaded into the database

  Scenario: Foundation categorization system properly categorizes foundations with enhanced Swedish categories
    When I trigger the foundation categorization job
    Then all foundations should be analyzed based on their purpose field
    And each foundation should receive an appropriate Swedish category
    And the categories should accurately reflect the foundation's purpose
    And the database should store these categories for later retrieval

  Scenario: Admin user can access protected admin endpoints
    Given I have valid admin credentials
    When I make a request to an admin endpoint with authentication
    Then the request should be authorized
    And I should be able to perform administrative actions

  Scenario: Non-admin user cannot access admin endpoints
    Given I don't have valid admin credentials
    When I make a request to an admin endpoint without proper authentication
    Then the request should fail with a 401 Unauthorized error
    And I should not be able to perform administrative actions

  Scenario: Foundation synchronization updates database records
    Given the foundation sync service is available
    When I trigger foundation synchronization manually
    Then the database should be cleared of old foundations
    And new foundations should be downloaded from the external API
    And foundations should be stored in the database with complete information
    And the response should indicate success

  Scenario: Category reset functionality works correctly
    Given some foundations are already categorized
    When I trigger category reset
    Then all foundation categories should be reset
    And foundations should be marked as uncategorized
    And I should be able to trigger recategorization after reset

  Scenario: Database clearing removes all data safely
    Given the database contains foundations and applications
    When I trigger database clear
    Then all foundations should be removed from the database
    And all applications should be removed from the database
    And all profiles should be removed from the database
    And the response should confirm deletion counts