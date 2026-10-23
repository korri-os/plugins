{ edenPackage }:
{
  packages.eden = edenPackage;
  files.eden = "${edenPackage}/bin/eden";
}
