"""Material helpers for label applicator animation."""
import bpy


def create_label_material(name="LabelMat", color=(0.95, 0.95, 0.9, 1.0), texture_path=None):
    """Create a label material, optionally with image texture."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.4
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    if texture_path:
        import os
        if os.path.exists(texture_path):
            tex = nodes.new('ShaderNodeTexImage')
            tex.location = (-300, 0)
            tex.image = bpy.data.images.load(texture_path)
            links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])

    return mat


def create_backing_material(name="BackingMat"):
    """Create a matte paper-like material for backing strip."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (0.85, 0.82, 0.75, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.8
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat


def create_glass_material(name="VialGlass"):
    """Create a glass material for the vial."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)
    mix = nodes.new('ShaderNodeMixShader')
    mix.location = (300, 0)
    mix.inputs['Fac'].default_value = 0.7

    glass = nodes.new('ShaderNodeBsdfGlass')
    glass.location = (0, 100)
    glass.inputs['IOR'].default_value = 1.5
    glass.inputs['Roughness'].default_value = 0.05
    glass.inputs['Color'].default_value = (0.95, 0.97, 1.0, 1.0)

    diffuse = nodes.new('ShaderNodeBsdfDiffuse')
    diffuse.location = (0, -100)
    diffuse.inputs['Color'].default_value = (0.9, 0.92, 0.95, 1.0)

    links.new(diffuse.outputs['BSDF'], mix.inputs[1])
    links.new(glass.outputs['BSDF'], mix.inputs[2])
    links.new(mix.outputs['Shader'], output.inputs['Surface'])
    return mat


def create_metal_material(name="Metal", color=(0.6, 0.6, 0.65, 1.0)):
    """Create a brushed metal material for mechanical parts."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = 0.9
    bsdf.inputs['Roughness'].default_value = 0.3
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat
