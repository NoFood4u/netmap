{ pkgs ? import <nixpkgs> {} }:

pkgs.python3Packages.buildPythonApplication {
	pname = "NetMap";
	version = "1.0.0";

	propagatedBuildInputs = with pkgs.python3Packages; [
		tkinter
		appdirs
	];

	src = ./.;
	
	meta = {
		changelog = "";
		description = "Displays your download/upload speed live on a world map";
		homepage = "";
		mainProgram = "netmap";
	};
}
