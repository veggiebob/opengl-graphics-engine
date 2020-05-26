from tremor.core.entity import Entity
from tremor.core.scene import Scene
from tremor.graphics.mesh import Mesh
from tremor.loader.scene.scene_types import *
import numpy as np
import io


def parse_keyvalue(string):
    pair = string.split("\" \"", 1)
    pair[0] = pair[0].replace("\"", "", 1)
    pair[1] = "".join(pair[1].rsplit("\"", 1))
    return pair


def parse_ents(ent_str):
    ents = []
    current_ent = {}
    for line in str.split(ent_str, "\n"):
        line = line.strip()
        if line == "{":
            continue
        if line == "}":
            ents.append(current_ent)
            current_ent = {}
            continue
        if line == "":
            continue
        pair = parse_keyvalue(line)
        current_ent[pair[0]] = pair[1]
    return ents


def load_scene_file(filename) -> Scene:
    file = open(filename, "rb")
    contents = np.frombuffer(file.read(-1), dtype='byte')
    file_length = file.seek(0, io.SEEK_END)
    file = None
    stuf = struct.unpack_from("<4s", contents)
    if stuf[0] != b'TMF\b':
        raise Exception("Invalid format")
    directory = []
    for i in range(0, NUMBER_OF_CHUNKS):
        a = RawChunkDirectoryEntry.size() * i + HEADER_SIZE
        directory.append(RawChunkDirectoryEntry.deserialize(contents[a:a + RawChunkDirectoryEntry.size()]))
    for dir_ent in directory:
        if dir_ent.start + dir_ent.length > file_length:
            raise Exception("Malformed directory!")
    print("loaded directory entries")
    # vertex_chunk = VertexChunk.from_directory(contents, directory[VERTEX_CHUNK_INDEX])
    vertex_entry = directory[VERTEX_CHUNK_INDEX]
    # model_vertex_chunk = ModelVertexChunk.from_directory(contents, directory[MODEL_CHUNK_INDEX])
    model_vertex_entry = directory[MODEL_VERTEX_CHUNK_INDEX]
    face_chunk = FaceChunk.from_directory(contents, directory[FACE_CHUNK_INDEX])
    model_chunk = ModelChunk.from_directory(contents, directory[MODEL_CHUNK_INDEX])
    entity_chunk = EntityChunk.from_directory(contents, directory[ENTITY_CHUNK_INDEX])
    scene = Scene(filename)
    scene.setup_scene_geometry(contents[vertex_entry.start:vertex_entry.start + vertex_entry.length],
                               contents[model_vertex_entry.start:model_vertex_entry.start + model_vertex_entry.length],
                               face_chunk.faces)
    fake_ents = parse_ents(str(entity_chunk.contents, 'utf-8'))
    real_ents = []
    for ent in fake_ents:
        entity = Entity()
        entity.classname = ent["classname"]
        ent.pop("classname")
        if "origin" in ent:
            split = str.split(ent["origin"], " ")
            split[0] = float(split[0])
            split[1] = float(split[1])
            split[2] = float(split[2])
            entity.transform.set_translation(np.array(split, dtype='float32'))
            ent.pop("origin")
        if "model" in ent:
            model_name = ent["model"]
            if str.startswith(model_name, "*"): # internal model
                entity.mesh = Mesh()
                entity.mesh.is_scene_mesh = True
                model_name = int(model_name.replace("*", ""))
                entity.mesh.scene_model = model_chunk.models[model_name]
        for k,v in ent.items():
            setattr(entity, k, v)
        real_ents.append(entity)
    scene.entities = real_ents
    return scene