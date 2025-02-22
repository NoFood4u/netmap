import tkinter as tk
import appdirs, os, json, subprocess, threading, time, array

HOME_CONFIG_DIRECTORY = appdirs.user_config_dir(appname='netmap')
DEFAULT_COLORS = {
	"BG_COLOR": "#000000",
	"FG_COLOR": "#00ff00",
	"FG_DARK": "#119911",
	"COUNTRY_OUTLINE": "#000000",
	"COUNTRY_FILL": "#003300",
	"CONNECTION_IN": "#00ff66",
	"CONNECTION_OUT": "#44ff00"
}

color_config = ""
try:
	with open(f"{HOME_CONFIG_DIRECTORY}/colors.conf", "r", encoding="utf-8") as f:
		color_config = f.read()
except:
	for k, v in DEFAULT_COLORS.items():
		color_config += f"{k}: {v}\n"
	try:
		try:
			os.mkdir(HOME_CONFIG_DIRECTORY)
		except:
			pass
		with open(f"{HOME_CONFIG_DIRECTORY}/colors.conf", "w", encoding="utf-8") as f:
			f.write(color_config)
	except Exception as e:
		print(f"Failed to create config file: {e}")

try:
	for line in color_config.replace(" ", "").split("\n"):
		try:
			globals()[line.split(":")[0]] = line.split(":")[1]
		except:
			pass
except Exception as e:
	print(f"Failed to parse config file: {e}")

for k, v in DEFAULT_COLORS.items():
	if k not in globals():
		print(f'Color "{k}" not found in config file')
		globals()[k] = v
		try:
			with open(f"{HOME_CONFIG_DIRECTORY}/colors.conf", "a", encoding="utf-8") as f:
				f.write(f"{k}: {v}\n")
				print(f"Added line to config file ({k}: {v})")
		except Exception as e:
			print(f"Failed to add color {k} to config file: {e}")
		

MAP_WIDTH = 1000
MAP_HEIGHT = 507
raw_map_svg = {}
try:
	with open(f"map-svg.json", "r", encoding="utf-8") as f:
		raw_map_svg = json.load(f)
except Exception as e:
	raise Exception(f"Failed to parse map file: {e}")

map_svg = {}
for country, outline in raw_map_svg.items():
	map_svg[country] = []
	for line in outline[1:].split("M"):
		points = []
		for segment in line.split("L"):
			segmentXY = segment.split(",")
			points.append(float(segmentXY[0]))
			points.append(float(segmentXY[1]))
		map_svg[country].append(points)


print("loading geolocation database...")
GEOIP_STARTS = array.array("I")
GEOIP_ENDS = array.array("I")
GEOIP_COUNTRIES = []
try:
	with open(f"dbip-city-ipv4-num.csv", "r", encoding="utf-8") as f:
		for line in f.readlines():
			values = line.strip().split(",")
			GEOIP_STARTS.append(int(values[0]))
			GEOIP_ENDS.append(int(values[1]))
			GEOIP_COUNTRIES.append(values[2])
except Exception as e:
	raise Exception(f"Failed to parse IP geolocation database file: {e}")
print("finished")

def geolocate(ip):
	ip_digits = ip.split(".")
	if len(ip_digits) != 4:
		return ""
	ip_num = 0
	for i in range(4):
		ip_num += int(ip_digits[i]) * 256**(3-i)

	first = 0
	last = len(GEOIP_STARTS)
	middle = last // 2
	while True:
		if ip_num < GEOIP_STARTS[middle]:
			last = middle
			if last-first == 0:
				return ""
			middle = first + (last-first) // 2
		elif ip_num > GEOIP_ENDS[middle]:
			first = middle + 1
			if last-first == 0:
				return ""
			middle = first + (last-first) // 2
		else:
			return GEOIP_COUNTRIES[middle]


root = tk.Tk()
root.title("NetMap")
root.geometry("1000x500")
root.configure(bg=BG_COLOR)
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

canvas = tk.Canvas(root, bg=BG_COLOR, highlightbackground=FG_DARK)
canvas.grid(sticky="NSEW")

canvas_countries = {}
highlighted_countries = {}
current_redraw_map_instance = []
def redraw_map(event):
	map_stretch_x = canvas.winfo_width() / MAP_WIDTH
	map_stretch_y = canvas.winfo_height() / MAP_HEIGHT
	current_redraw_map_instance = [map_stretch_x, map_stretch_y]
	canvas.delete("all")
	canvas_point_ids = []
	canvas_arrow_ids = []
	for country, outline in map_svg.items():
		country_polygons = []
		for line in outline:
			nums = line.copy()
			for i in range(0, len(nums), 2):
				nums[i] *= map_stretch_x
				nums[i+1] *= map_stretch_y
			
			if current_redraw_map_instance != [map_stretch_x, map_stretch_y]:
				return
			
			color = COUNTRY_FILL
			if country in highlighted_countries:
				color = highlighted_countries[country]

			country_polygons.append(canvas.create_polygon(*nums, outline=COUNTRY_OUTLINE, fill=color, width=1))

		try: # a country might not exist on the map
			canvas_countries[country] = country_polygons
		except:
			pass

root.bind("<Configure>", redraw_map)

def highlight_country(country, color):
	highlighted_countries[country] = color
	for polygon in canvas_countries[country]:
		canvas.itemconfig(polygon, fill=color)
def unhighlight_country(country):
	for polygon in canvas_countries[country]:
		canvas.itemconfig(polygon, fill=COUNTRY_FILL)

buffer_udp_in = {}
buffer_udp_out = {}
buffer_tcp_in = {}
buffer_tcp_out = {}

def rgb_to_color(rgb):
	color = "#"
	for i in range(3):
		component = hex(rgb[i])[2:]
		if len(component) == 1:
			component = "0" + component
		color += component
	return color

def process_ip(new_country_colors, ip, size, rgb_index):
	country = geolocate(ip)
	if country != "":
		color_rgb = [0, 51, 0]
		try:
			color_rgb = new_country_colors[country]
		except:
			pass
		color_rgb[rgb_index] = max(color_rgb[rgb_index], 25)
		color_rgb[rgb_index] = min(color_rgb[rgb_index] + size//3000, 255)
		new_country_colors[country] = color_rgb

def update_thread():
	global highlighted_countries, buffer_udp_in, buffer_udp_out, buffer_tcp_in, buffer_tcp_out
	
	while True:
		time.sleep(1)
		udp_in = buffer_udp_in.copy()
		buffer_udp_in = {}
		tcp_in = buffer_tcp_in.copy()
		buffer_tcp_in = {}
		udp_out = buffer_udp_out.copy()
		buffer_udp_out = {}
		tcp_out = buffer_tcp_out.copy()
		buffer_tcp_out = {}

		new_country_colors = {}
		
		for ip, size in udp_in.items():
			process_ip(new_country_colors, ip, size, 0)
		for ip, size in tcp_in.items():
			process_ip(new_country_colors, ip, size, 0)
		for ip, size in udp_out.items():
			process_ip(new_country_colors, ip, size, 2)
		for ip, size in tcp_out.items():
			process_ip(new_country_colors, ip, size, 2)

		for country in highlighted_countries:
			try:
				unhighlight_country(country)
			except:
				pass
		highlighted_countries = {}
		for country, color_rgb in new_country_colors.items():
			try:
				highlight_country(country, rgb_to_color(color_rgb))
			except:
				pass

def capture_thread(process):
	for line in process.stdout:
		if line[0].isdigit():
			try:
				packet = line.split(" ")
				ip_from = packet[2][:packet[2].rfind(".")]
				ip_to = packet[4][:packet[4].rfind(".")]
				size = int(line[line.rfind(" ")+1:])
				ip_remote = ip_to
				is_download = True
				if ip_to.startswith("192.168.1."):
					ip_remote = ip_from
					is_download = False
				
				if packet[5] == "UDP,":
					if is_download:
						if ip_remote in buffer_udp_in:
							buffer_udp_in[ip_remote] += size
						else:
							buffer_udp_in[ip_remote] = size
					else:
						if ip_remote in buffer_udp_out:
							buffer_udp_out[ip_remote] += size
						else:
							buffer_udp_out[ip_remote] = size
				else:
					if is_download:
						if ip_remote in buffer_tcp_in:
							buffer_tcp_in[ip_remote] += size
						else:
							buffer_tcp_in[ip_remote] = size
					else:
						if ip_remote in buffer_tcp_out:
							buffer_tcp_out[ip_remote] += size
						else:
							buffer_tcp_out[ip_remote] = size
			except:
				pass

subprocess.check_output("sudo echo echo", shell=True, text=True) # make sure we have sudo privilages
process = subprocess.Popen(["sudo", "tcpdump", "-n"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

t1 = threading.Thread(target=capture_thread, args=(process,))
t1.daemon = True
t1.start()
t2 = threading.Thread(target=update_thread)
t2.daemon = True
t2.start()



root.mainloop()
