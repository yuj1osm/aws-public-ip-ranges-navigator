# Requirements Document

## Introduction

The AWS Public IP Ranges Navigator is a Python Terminal User Interface (TUI) application that
fetches Amazon Web Services' officially published public IP range data and lets a user browse
and filter it interactively. The application is launched from the command line without requiring
the user to memorize command-line option arguments, and is operated primarily through keyboard
navigation (arrow keys and a small set of hotkeys).

AWS publishes its public IP ranges as a JSON document at a fixed URL. Because these ranges change
over time, the application fetches the current data on demand rather than relying on a bundled
snapshot. The interface presents a three-panel layout: a selection area (Regions list and Services
list) on the left, a results table on the right listing matching IP prefixes, and an action/key bar
along the bottom.

The application is intended for global public release. All intermediate artifacts and documentation
are written in English.

## Glossary

- **Navigator**: The overall TUI application described by this document.
- **Data_Fetcher**: The component responsible for retrieving the AWS IP ranges JSON document over HTTPS.
- **Data_Store**: The in-memory representation of the parsed AWS IP ranges data held by the Navigator.
- **IP_Prefix**: A single AWS public IP range entry consisting of a CIDR block, a region, and a service.
- **CIDR**: A Classless Inter-Domain Routing block string (for example, `52.94.0.0/22`) that identifies an IP prefix.
- **Region**: The AWS region identifier associated with an IP prefix (for example, `ap-northeast-1`).
- **Service**: The AWS service label associated with an IP prefix (for example, `EC2`, `S3`, `CLOUDFRONT`, `ROUTE53`, or `AMAZON`).
- **Region_List**: The selection list displaying the distinct regions available for filtering, including an `ALL` entry. The Region_List is rendered as a vertical, independently scrollable list.
- **Service_List**: The selection list displaying the distinct services available for filtering, including an `ALL` entry. The Service_List is rendered as a vertical, independently scrollable list.
- **Selection_Panel**: The left-hand area containing the Region_List and the Service_List.
- **Active_Panel**: The list (Region_List or Service_List) that currently receives keyboard navigation input.
- **Results_Table**: The right-hand table listing the IP_Prefix entries that match the current filter.
- **Action_Bar**: The bottom bar displaying the available hotkeys and their actions.
- **Data_Source_URL**: The fixed URL `https://ip-ranges.amazonaws.com/ip-ranges.json` from which IP ranges data is fetched.
- **Filter_Selection**: The currently selected Region and Service used to filter IP_Prefix entries in the Results_Table.

## Requirements

### Requirement 1: Command-line launch

**User Story:** As a user, I want to launch the application with a single command and no option arguments, so that I do not need to memorize command-line flags.

#### Acceptance Criteria

1. WHEN the user runs the application entry-point script with no command-line arguments, THE Navigator SHALL start and display the three-panel interface.
2. IF the user supplies one or more command-line arguments, THEN THE Navigator SHALL start and display the three-panel interface using the same default behavior as when no arguments are supplied.
3. WHEN the Navigator starts, THE Navigator SHALL initiate a fetch of the AWS IP ranges data before enabling interactive navigation.

### Requirement 2: Fetch current AWS IP ranges data

**User Story:** As a user, I want the application to fetch the latest AWS IP ranges from the official source, so that I browse current information rather than a stale snapshot.

#### Acceptance Criteria

1. WHEN the Navigator starts, THE Data_Fetcher SHALL retrieve the IP ranges document from the Data_Source_URL over HTTPS.
2. WHEN the user activates the reload action, THE Data_Fetcher SHALL retrieve the IP ranges document from the Data_Source_URL over HTTPS again.
3. WHEN the Data_Fetcher completes a reload retrieval successfully, THE Navigator SHALL replace the entire contents of the Data_Store with the newly parsed IP_Prefix entries.
4. IF the Data_Fetcher fails to complete a reload retrieval, THEN THE Navigator SHALL retain the existing contents of the Data_Store unchanged and SHALL display an error message stating that the data could not be retrieved.
5. WHEN the Data_Fetcher retrieves the IP ranges document, THE Navigator SHALL parse the document into a set of IP_Prefix entries, each containing a CIDR, a Region, and a Service.
6. IF the Data_Fetcher does not receive a complete IP ranges document within 15 seconds of initiating a retrieval, THEN THE Navigator SHALL abort the retrieval, SHALL display an error message stating that the data could not be retrieved, and SHALL remain running.
7. IF the retrieved document cannot be parsed into at least one IP_Prefix entry, THEN THE Navigator SHALL display an error message stating that the data could not be parsed, SHALL retain the existing contents of the Data_Store unchanged, and SHALL remain running.
8. IF a retrieved IP_Prefix entry is missing a CIDR, a Region, or a Service, THEN THE Navigator SHALL exclude that entry from the parsed set and SHALL continue parsing the remaining entries.

### Requirement 3: Selection panel with Regions and Services

**User Story:** As a user, I want to see the available regions and services in selectable lists, so that I can choose what to filter by.

#### Acceptance Criteria

1. WHEN the Data_Store is populated, THE Region_List SHALL display the distinct Region values present in the Data_Store together with an `ALL` entry.
2. WHEN the Data_Store is populated, THE Service_List SHALL display the distinct Service values present in the Data_Store together with an `ALL` entry.
3. THE Selection_Panel SHALL display the Region_List and the Service_List stacked vertically on the left side of the interface, with the Region_List positioned above the Service_List.
4. THE Selection_Panel SHALL render the Region_List as a vertical list in which the Region entries are arranged top-to-bottom.
5. THE Selection_Panel SHALL render the Service_List as a vertical list in which the Service entries are arranged top-to-bottom.
6. WHEN the Region_List contains more items than fit within its visible row area, THE Navigator SHALL make the Region_List independently scrollable so that the Region_List can be scrolled without changing the visible portion of the Service_List.
7. WHEN the Service_List contains more items than fit within its visible row area, THE Navigator SHALL make the Service_List independently scrollable so that the Service_List can be scrolled without changing the visible portion of the Region_List.
8. THE Navigator SHALL highlight the currently selected item in the Active_Panel.

### Requirement 4: Panel switching

**User Story:** As a user, I want to switch focus between the Regions list and the Services list, so that I can change either filter dimension using the keyboard.

#### Acceptance Criteria

1. THE Navigator SHALL designate exactly one of the Region_List or the Service_List as the Active_Panel at any time.
2. WHEN the user presses the Tab key, THE Navigator SHALL change the Active_Panel from the Region_List to the Service_List, or from the Service_List to the Region_List.
3. WHEN the Active_Panel changes, THE Navigator SHALL visually indicate which panel is active.

### Requirement 5: Keyboard navigation within a panel

**User Story:** As a user, I want to move the selection within the active list using the arrow keys, so that I can pick an item without a mouse.

#### Acceptance Criteria

1. WHEN the user presses the Down arrow key AND the selected item is not the last item in the Active_Panel, THE Navigator SHALL move the selection to the next item in the Active_Panel within 100 milliseconds.
2. WHEN the user presses the Up arrow key AND the selected item is not the first item in the Active_Panel, THE Navigator SHALL move the selection to the previous item in the Active_Panel within 100 milliseconds.
3. WHEN the user presses the Down arrow key AND the selected item is the last item in the Active_Panel, THE Navigator SHALL keep the selection on the last item.
4. WHEN the user presses the Up arrow key AND the selected item is the first item in the Active_Panel, THE Navigator SHALL keep the selection on the first item.
5. WHILE the Active_Panel contains no items, WHEN the user presses the Up arrow key or the Down arrow key, THE Navigator SHALL make no change to the selection.
6. WHEN the number of items in the Active_Panel exceeds the visible rows AND the selection moves, THE Navigator SHALL scroll the Active_Panel so that the selected item is fully within the visible row area within 100 milliseconds.

### Requirement 6: Filtering the results table

**User Story:** As a user, I want the results table to reflect my selected region and service, so that I see only the IP prefixes that match my filter.

#### Acceptance Criteria

1. WHEN the Filter_Selection changes, THE Results_Table SHALL display the IP_Prefix entries whose Region equals the selected Region and whose Service equals the selected Service, and SHALL exclude every IP_Prefix entry that does not match both criteria.
2. WHERE the selected Service is `ALL`, THE Results_Table SHALL display the IP_Prefix entries whose Region equals the selected Region regardless of Service.
3. WHERE the selected Region is `ALL`, THE Results_Table SHALL display the IP_Prefix entries whose Service equals the selected Service regardless of Region.
4. THE Results_Table SHALL display each matching IP_Prefix as a row containing a sequential row number that starts at 1 and increments by 1 without gaps in top-to-bottom display order, the CIDR, the Region, and the Service.
5. THE Results_Table SHALL display the count of matching IP_Prefix entries in the Results_Table header, where the count equals the number of displayed rows.
6. WHEN no IP_Prefix entry matches the Filter_Selection, THE Results_Table SHALL display zero rows and a matching count of zero.

### Requirement 7: Clearing the filter

**User Story:** As a user, I want to clear my current filter, so that I can quickly return to an unfiltered view.

#### Acceptance Criteria

1. WHEN the user activates the clear-filter action, THE Navigator SHALL reset the Filter_Selection to its initial state.
2. WHEN the Filter_Selection is reset, THE Results_Table SHALL update to reflect the reset Filter_Selection.

### Requirement 8: Action/key bar

**User Story:** As a user, I want an always-visible key bar, so that I can discover the available actions without consulting external documentation.

#### Acceptance Criteria

1. THE Action_Bar SHALL be displayed along the bottom of the interface.
2. THE Action_Bar SHALL display the clear-filter action bound to the `x` key.
3. THE Action_Bar SHALL display the quit action bound to the `q` key.
4. THE Action_Bar SHALL display the reload-data action bound to the `r` key.
5. THE Action_Bar SHALL display the switch-pane action bound to the Tab key.
6. THE Action_Bar SHALL display the navigate action bound to the Up and Down arrow keys.

### Requirement 9: Reload data action

**User Story:** As a user, I want to reload the data on demand, so that I can refresh to the latest AWS IP ranges without restarting the application.

#### Acceptance Criteria

1. WHEN the user presses the `r` key, THE Navigator SHALL initiate a reload of the IP ranges data through the Data_Fetcher.
2. WHEN a reload completes successfully, THE Navigator SHALL rebuild the Region_List and the Service_List from the updated Data_Store.
3. WHEN a reload completes successfully, THE Results_Table SHALL update to reflect the current Filter_Selection against the updated Data_Store.

### Requirement 10: Quit

**User Story:** As a user, I want to quit the application with a single keystroke, so that I can exit cleanly when finished.

#### Acceptance Criteria

1. WHEN the user presses the `q` key, THE Navigator SHALL terminate the interactive session and return control to the shell.
2. WHEN the Navigator terminates, THE Navigator SHALL restore the terminal to its normal (non-TUI) display state.

### Requirement 11: Parse AWS IP ranges document

**User Story:** As a developer, I want the IP ranges document parsed into structured entries, so that filtering and display operate on well-defined data.

#### Acceptance Criteria

1. WHEN an IP ranges document containing the expected prefix collection is provided, THE Navigator SHALL parse each IPv4 prefix entry that has a non-empty CIDR, Region, and Service into an IP_Prefix containing the CIDR, the Region, and the Service, and SHALL store the resulting IP_Prefix entries in the Data_Store.
2. IF the IP ranges document cannot be structurally interpreted as a document, THEN THE Navigator SHALL report a parse error to the caller, SHALL leave the Data_Store unchanged, and SHALL indicate to the caller that no entries were parsed.
3. IF the IP ranges document is well-formed but does not contain the expected prefix collection, THEN THE Navigator SHALL report a parse error to the caller, SHALL leave the Data_Store unchanged, and SHALL indicate to the caller that the prefix collection was absent.
4. IF an individual prefix entry is missing, empty, or blank for its CIDR, its Region, or its Service value, THEN THE Navigator SHALL exclude that entry from the Data_Store and SHALL continue parsing the remaining entries.

### Requirement 12: Mouse selection and scrolling

**User Story:** As a user, I want to select and scroll items in either selection list with my mouse, so that I can operate the interface without relying only on the keyboard.

#### Acceptance Criteria

1. WHEN the user clicks an item within the visible row area of the Region_List, THE Navigator SHALL set that item as the selected item in the Region_List and SHALL make the Region_List the Active_Panel.
2. WHEN the user clicks an item within the visible row area of the Service_List, THE Navigator SHALL set that item as the selected item in the Service_List and SHALL make the Service_List the Active_Panel.
3. WHEN the selected item in the Region_List or the Service_List changes as a result of a mouse click, THE Navigator SHALL update the Filter_Selection and the Results_Table to reflect the new selection consistent with Requirement 6.
4. IF the user clicks within a list's visible row area but on a position that contains no item, THEN THE Navigator SHALL leave the selected item of that list unchanged and SHALL make that list the Active_Panel.
5. WHEN a list contains more items than fit within its visible row area, THE Navigator SHALL provide a scrollbar for that list and SHALL allow the user to scroll that list using the mouse scroll wheel or the scrollbar independently of the other list, without changing the selected item or the Active_Panel of either list.
6. WHILE a list contains a number of items less than or equal to the number of rows in its visible row area, THE Navigator SHALL NOT provide a scrollbar for that list and SHALL ignore mouse scroll wheel input directed at that list.
7. WHEN the user scrolls the Region_List or the Service_List using the mouse scroll wheel or the scrollbar without clicking an item, THE Navigator SHALL change only the visible portion of that list and SHALL leave the selected item of that list, the Filter_Selection, and the Results_Table unchanged.
