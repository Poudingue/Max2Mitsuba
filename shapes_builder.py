import os
import tools
import config
import xml.etree.ElementTree as etree


def build(root, geometries, materials_ids, links_simple, links_revert):
	"""
	Exports all the geometry into a folder for later use in the scene.
	Return a list of ids for the geometry
	"""
	if config.verbose : print("shapes_builder_fbx launched")
	savepath = config.filepath+"export\\meshes\\"
	if not os.path.exists(savepath) :
		os.makedirs(savepath)

	comment = etree.Comment("Shapes.")
	root.append(comment)

	geometries_id = []
	# Only keep geometries with polygonvertex
	geometries = [geometry for geometry in geometries if geometry.find("PolygonVertexIndex") != None ]

	for geometry in geometries :

		id, type, obj = geometry.get("value").replace("::","").split(", ")
		if obj != "Mesh" : print("Unknown Geometry obj : "+obj+" (id="+id+")")
		geometries_id.append(id)

		if id not in links_revert :
			if verbose : print("Model "+id+" never used. Not writing it to file.")
		else :
			properties = tools.getProperties(geometry)
			linked_materials = links_revert[id] if id in links_revert else [] # Get the model(s) containing this geometry (Only the models reference materials)
			if len(linked_materials) == 1 :
				linked_materials = links_simple[linked_materials[0]]
			else :
				print("Multiple models containing geometry "+id+" ???")
				linked_materials = []
			linked_materials = [link for link in linked_materials if link in materials_ids] #Only keep ids of materials
			# I think that the index for materials is based on the order they appear in the file
			# Maybe not, but i see no other info in the fbx to know that, so that's what i use and it seems to work

			vertices_data = geometry.find("Vertices")
			nb_vertices = int(vertices_data.get("value").replace("*",""))

			polygons_data = geometry.find("PolygonVertexIndex")
			nb_poly_ind = int(polygons_data.get("value").replace("*",""))

			edges_data    = geometry.find("Edges")
			nb_edges    = int(   edges_data.get("value").replace("*",""))

			normal_layer  = geometry.find("LayerElementNormal")
			if normal_layer != None :
				normals_data  = normal_layer.find("Normals")
				normalsW_data = normal_layer.find("NormalsW")
				nb_normals  = int( normals_data.get("value").replace("*",""))
				nb_normalsW = int(normalsW_data.get("value").replace("*",""))

			uv_layer      = geometry.find("LayerElementUV")
			if uv_layer != None :
				uv_data       = uv_layer.find("UV")
				uv_index_data = uv_layer.find("UVIndex")
				nb_uv_data  = int(      uv_data.get("value").replace("*",""))
				nb_uv_index = int(uv_index_data.get("value").replace("*",""))

			material_layer= geometry.find("LayerElementMaterial")
			if material_layer != None :
				material_data = list(map(int, material_layer.find("Materials").find("a").text.split(",")))
				if material_layer.find("MappingInformationType").text == "AllSame" :
					material_data = nb_poly_ind * [material_data[0]]

			vertices_in = [tools.str2float2str(num) for num in vertices_data.find("a").text.split(",")]
			polygons_in =                        list(map(int, polygons_data.find("a").text.split(",")))
			edges_in    = [tools.str2float2str(num) for num in    edges_data.find("a").text.split(",")]
			normals_in  = [tools.str2float2str(num) for num in  normals_data.find("a").text.split(",")]
			normalsW_in = [tools.str2float2str(num) for num in normalsW_data.find("a").text.split(",")]
			uv_in       = [tools.str2float2str(num) for num in       uv_data.find("a").text.split(",")]
			uv_index_in =                        list(map(int, uv_index_data.find("a").text.split(",")))

			vertices, polygon_vertex_index, normals, uv = [], [], [], []

			if nb_vertices % 3 != 0 :
				print("Points values not a multiple of 3 !")
			for i in range(int(nb_vertices / 3)) :
				vertices.append(vertices_in[3*i : 3*i+3])


			curr_vertex = []
			for index in polygons_in :
				if index < 0 :
					curr_vertex.append(-index-1)
					polygon_vertex_index.append(curr_vertex)
					curr_vertex = []
				else :
					curr_vertex.append(index)
			nb_polygons = len(polygon_vertex_index)

			if normal_layer != None :
				normal_type = normal_layer.find("ReferenceInformationType").text
				if normal_type == "Direct" :
					for i in range(int(nb_normals/3)) :
						normals.append(normals_in[3*i : 3*i+3])
				elif normal_type == "IndexToDirect" :
					# TODO
					print("NORMAL INDEXTODIRECT DOESN'T WORK RIGHT NOW")
				else :
					print("Unknown ReferenceInformationType for normal in obj "+id)
			else :
				print("NO NORMALS for object with id "+id)

			if uv_layer != None :
				uv_type = uv_layer.find("ReferenceInformationType").text
				if uv_type == "Direct" :
					for i in range(int(nb_uv_data/2)) :
						uv.append(uv_in[2*i : 2*i+2])
				elif uv_type == "IndexToDirect" :
					for i in range(int(nb_uv_index)) :
						index = uv_index_in[i]
						uv.append(uv_in[2*index : 2*index+2])
				else :
					print("Unknown ReferenceInformationType for uv in obj "+id)
					uv = ["0 0"] * nb_poly_ind
			else :
				if config.verbose : print("No uv for object with id "+id+". Using default of 0, 0")
				uv = ["0 0"] * nb_poly_ind


			materials = geometry.find("LayerElementMaterial")
			if materials != None :
				materials = list(map(int, materials.find("Materials").find("a").text.split(",")))
			if materials == None or len(materials) <= 1 :
				materials = [0 for i in range(nb_polygons)]
			max_material  = max(materials)

			# The shapegroup will contain all meshes with different materials, and allow instanciation
			shapegroup = tools.create_obj(root, "shape", "shapegroup", id)

			# Initialize
			for i in range(max_material + 1) :

				vertex_text = []
				poly_index  = []
				total_index = 0
				curr_polygon_vertex_num = 0

				for j in range(len(polygon_vertex_index)) :
					vertex_indexes = polygon_vertex_index[j]
					curr_poly_index = []
					for k in range(len(vertex_indexes)) :

						# Only keep polygons with the current material
						if material_layer == None or material_data[j] == i :
							curr_poly_index.append(str(total_index))
							total_index += 1
							vertex_index = vertex_indexes[k]
							curr_vertex_text  = " ".join(vertices[vertex_index])            + " "
							curr_vertex_text += " ".join( normals[curr_polygon_vertex_num]) + " "
							curr_vertex_text += " ".join(      uv[curr_polygon_vertex_num])
							vertex_text.append(curr_vertex_text)
						curr_polygon_vertex_num += 1

					# Generate multiple triangle to replace polygons (not supported by Mitsuba Renderer)
					if len(curr_poly_index) > 3 :
						for k in range(len(curr_poly_index) - 2) :
							curr_poly = [curr_poly_index[0]] + curr_poly_index[k+1:k+3]
							poly_index.append(curr_poly)
					elif len(curr_poly_index) > 0 :
						poly_index.append(curr_poly_index)

				if vertex_text != [] : # Export only non-empty objects
					output = open(savepath+id+"_"+str(i)+".ply", "w")
					output.write("ply\n")
					output.write("format ascii 1.0\n")
					output.write("element vertex " + str(len(vertex_text))+"\n")
					output.write(
"""property float32 x
property float32 y
property float32 z
property float32 nx
property float32 ny
property float32 nz
property float32 u
property float32 v
""")
					output.write("element face "+str(len(poly_index))+"\n")
					output.write("property list uint8 int32 vertex_indices\n")
					output.write("end_header\n")

					for vert in vertex_text :
						output.write(vert+"\n")

					for poly in poly_index : # Only triangles
						output.write("3 "+" ".join(poly)+"\n")
					shape = tools.create_obj(shapegroup, "shape", "ply")
					tools.set_value(shape, "string", "filename", "meshes/"+id+"_"+str(i)+".ply")

					try :
						tools.set_value(shape, "ref", "bsdf", linked_materials[i])
					except IndexError :
						if config.verbose : print("No material found for object "+id+", index "+str(i))

	return geometries_id
