# Temporary: korri e39102089's generated plugin contract

TEMPORARY. Remove this folder when the `korri` flake input moves to a korri
commit on main that holds korri e39102089 (the Steam engine under any publisher
namespace, ADR 0045). Then the Steam declaration check takes the contract from
the `korri` input again, like every other plugin.

These three files are byte copies of korri-os/korri commit `e39102089`
`contracts/generated/{korrid,surface,settings}.ts`. They are generated files: do
not edit them. They are here only because `ReleaseDiscoveryInput.pluginId`
exists in that commit and not yet in the pinned korri (6f6fa81). Only the
`korri-steam-declaration` check reads them (nix/default.nix); every other
plugin keeps the pinned korri's contract.
