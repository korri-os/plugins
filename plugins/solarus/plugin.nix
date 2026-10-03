{ solarusPackage }:
{
  packages.solarus = solarusPackage;
  files.solarus = "${solarusPackage}/bin/solarus-run";
}
