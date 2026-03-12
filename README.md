# MuPlugins

## What is this?
The MuPlugins are a set of official plugins for MuFoundry. The official project skeleton, `MuCrucible`, assumes they'll be used, though only `Core` and `Telnet` are assumed and only `Core` would be required.

## Do I need them?
In short, no. But for a longer answer: if you want to operate without `Core`, you will need to implement a great deal of equivalent functionality such as user registration, authentication, and permissions, and the approach for handling bringing player characters online and how event streaming works.

So it's highly recommended to at least use the `Core` plugin.

## Available Plugins
- `Core`: Main framework for users and player characters, authentication, event streaming, extensible rule-based access control "lock" functions, postgresql infrastructure and migration support.
- `Telnet`: First-class support for legacy telnet clients, with features such as GMCP, MCCP2, NAWS, MTTS, and more.
- `BBS`: Bulletin Board System based on [Myrddin's BBS](https://github.com/myrddin/bbs) with further enhancements.
- `Channels`: Real-time chat channels with full logging and rule-based access control. Its schema provides namespaces and categories so plugins can create custom channel-like systems. For instance, the default channels might be OOC (out-of-character), and an alternate system called Radio might be used for IC (in-character) communication.
- `Factions`: Provides a simple but flexible Faction system for organizing player characters into groups, guilds, businesses, etc. Factions can be categorized and provide numeric ranks. Permissions can be granted "to all faction members", to specific ranks, or to individual characters, and then used by `Core` lock system.

- More coming soon!
