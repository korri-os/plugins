{ pyxelPackage }:
{
  packages.pyxel = pyxelPackage;
  files.pyxel = "${pyxelPackage}/bin/korri-pyxel";
}
