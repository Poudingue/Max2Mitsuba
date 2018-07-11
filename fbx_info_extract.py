import fbx2xml
import os
import xml.etree.cElementTree as etree
import xml.dom.minidom as dom

verbose = True

def fbx_extract(filename):
	print("fbx_info_extract launched")

	fbx2xml.transform(filename)

	inputfile = open(filename+"_fbx.xml", encoding="utf8")
	inputdata = dom.parse(inputfile)
	inputfile.close()

	big_dictionnary = {}

	connections_list = inputdata.getElementsByTagName("Connections")[0]

	comments = connections_list.getElementsByTagName("comment")
	connections = connections_list.getElementsByTagName("C")

	if len(comments)!=len(connections) :
		print("comments and connections are not of the same length")
		exit(1)

	for i in range(len(comments)) :
		comment    = comments[i]
		connection = connections[i]

		objects = str(comment.firstChild.nodeValue).split(", ")
		ids     = str(connection.firstChild.nodeValue).split(",")
		object1, object2 = objects
		if object1.startswith("Template"):
			object1type, obj1num, obj1name = object1.split(" - ")
			object1name = obj1name+"_"+obj1num
		else :
			object1type, object1name = object1.split("::")
		object2type, object2name = object2.split("::")

		# Not sure whrat «something» is supposed to be yet.class
		# But when it's OO, there are 3 arguments, 4 else.
		if ids[0] == "OO":
			complementary = "None"
			something, id1, id2 = ids
		else :
			something, id1, id2, complementary = ids

		if object1name=="":
			object1name=object2name
		if object1name!="T" and object1name!="R" and object1name!="S" :
			object1name = object1type +"_"+ object1name.replace(" ","_")
			id_in_dict1 = big_dictionnary.get(object1name)
			if id_in_dict1!=None and id_in_dict1!=id1 :
				if verbose :
					print(object1name+" already in dict with id : "+ id1 +" vs "+id_in_dict1)
			else : big_dictionnary[object1name]=id1

		object2name = object2type + "_" + object2name.replace(" ","_")
		id_in_dict2 = big_dictionnary.get(object2name)
		if id_in_dict2!=None and id_in_dict2!=id2 :
			print(object2name +" already in dict with id : "+ id2 +" vs "+id_in_dict2)
		else : big_dictionnary[object2name]=id2

	objects_list = inputdata.getElementsByTagName("Objects")[0]
	geometry_list = objects_list.getElementsByTagName("Geometry")
	geometry_temp_dict = {}
	for geometry in geometry_list :

		id = geometry.getAttribute("value").split(",")[0]
		geometry_temp_dict[id]=geometry
	# Xml structure of the correct object can be accessed directly
	GeometryInfos = {}

	for stuff in big_dictionnary :
		if stuff.startswith("Geometry") :
			GeometryInfos[stuff]=geometry_temp_dict[big_dictionnary[stuff]]
			# if verbose :
			# 	print("  known stuff : "+stuff)
		# elif verbose :
		# 	print("Unknown stuff : "+stuff)

	if not os.path.exists("fbxinfos") :
		os.makedirs("fbxinfos")
	for stuff in GeometryInfos :
		outputdata = GeometryInfos[stuff]
		# Replace uv+uvindex by simple uv list
		getLayerUv = outputdata.getElementsByTagName("LayerElementUV")
		if getLayerUv == [] :
			print("Empty layeruv in "+stuff)
			uvout=""
		else :
			layerUv = getLayerUv[0]
			uvs = layerUv.getElementsByTagName("UV")[0].getElementsByTagName("a")[0].firstChild.nodeValue.split(",")
			uvsindex = layerUv.getElementsByTagName("UVIndex")[0].getElementsByTagName("a")[0].firstChild.nodeValue.split(",")
			uvout=""
			for i in range(len(uvsindex)) :
				curr_index = int(uvsindex[i])
				uvout+=(uvs[2*curr_index]+" "+uvs[2*curr_index+1]+",")
		# Write in the correct file
		output_uv = open("fbxinfos/"+stuff+"_uv.txt", "w", encoding="utf8")
		output_uv.write(uvout)

		outputfile = open("fbxinfos/"+stuff+".xml", "w", encoding="utf8")
		outputfile.write(GeometryInfos[stuff].toxml())
		if verbose :
			print("Wrote "+stuff+" info")