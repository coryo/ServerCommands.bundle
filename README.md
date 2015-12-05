# ServerCommands.bundle
Plex Media Server Channel that uses the Plex Media API to perform some tasks.

### Usage:
**Authorization**: The channel needs to be authorized to access server functions. To do this, access the channel as the user that has the required permission and press the button. This stores the users X-Plex-Token, and uses it to make requests at the server. Once the channel has the token, ANY user will be able to access the functions.

**De-authorization**: access the channel as the same user who authorized it. There will be a deauthorize button.

### Current Functions:
  * **Libraries**
    * Refresh, Analyze, Optimize, Clean Bundles, Empty Trash
