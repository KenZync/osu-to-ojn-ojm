import configparser

def generate_default_config(config_file):
	print("Generating Default Configuration!")
	config_file["Path"]={
	"Input":"Input",
	"Inprogress" : "Inprogress",
	"Output" : "Output"
	}

	config_file["Default"]={
	"o2maID":"1000",
	"level" : "1",
	"multiplyBPM" : "1",
	"offset" : "0",
	"useTitle" : "True"
	}

	config_file.add_section("Automation")
	config_file.set("Automation", "autoID", "False")
	config_file.set("Automation", "autoRemoveInput", "False")
	config_file.set("Automation", "autoRemoveInprogress", "False")

	config_file["Path"]={
	"Input":"Input",
	"Inprogress" : "Inprogress",
	"Output" : "Output"
	}

	with open("config.ini", 'w') as configfileObj:
		config_file.write(configfileObj)
		configfileObj.flush()
		configfileObj.close()

def read_config():
	config_file = configparser.ConfigParser()
	try:
		print("Reading Configuration!")
		config_file.read('config.ini')
		open("config.ini", "r")
	except FileNotFoundError:
		print("Config file not found!")
		generate_default_config(config_file)
		config_file.read('config.ini')
	return config_file