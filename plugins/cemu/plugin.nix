{ cemuPackage }:
{
  packages.cemu = cemuPackage;
  files.cemu = "${cemuPackage}/bin/cemu";
}
