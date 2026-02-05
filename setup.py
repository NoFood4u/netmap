from setuptools import setup, find_packages

setup(name='NetMap',
	version='1.0',
	packages=find_packages(),
	scripts=["src/netmap/netmap.py"],
	data_files=[("bin", ["dbip-city-ipv4-num.csv", "map-svg.json"])],
	entry_points={
	'gui_scripts': [
		'netmap = netmap:main',
	]
	}
)
