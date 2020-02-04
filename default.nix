{ pkgs ? import <nixpkgs> {  } }:

let
  python37-spotify-title = pkgs.python37.withPackages (p: with p; [
    requests
    dbus-python
    pygobject3
  ]);
in

pkgs.stdenvNoCC.mkDerivation {
  name = "python37-spotify-title";
  nativeBuildInputs = with pkgs; [
    python37-spotify-title
  ];
}


