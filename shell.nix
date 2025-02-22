let
	pkgs = import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/a45fa362d887f4d4a7157d95c28ca9ce2899b70e.tar.gz") {};
in pkgs.mkShell {
	buildInputs = with pkgs; [
		tcpdump
	];
	packages = [
		(pkgs.python3.withPackages (python-pkgs: with python-pkgs; [
			tkinter
			appdirs
		]))
	];
}

