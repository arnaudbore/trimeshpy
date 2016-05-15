# Etienne.St-Onge@usherbrooke.ca

from trimesh_class import TriMesh
import vtk
import vtk.util.numpy_support as ns
import vtk_util as vtk_u

import numpy as np


class TriMesh_Vtk(TriMesh):
    # Get and Set
    # PolyData

    def __init__(self, triangles, vertices, dtype=np.float64, atol=1e-8, assert_args=True):
        if isinstance(triangles, basestring):
            self.__polydata__ = vtk_u.load_polydata(triangles)
            self.__polydata_is_up_to_date__ = True
            TriMesh.__init__(self, self.get_polydata_triangles(), self.get_polydata_vertices(), dtype=dtype, atol=atol, assert_args=assert_args)
        elif isinstance(vertices, basestring):
            self.__polydata__ = vtk_u.load_polydata(vertices)
            self.__polydata_is_up_to_date__ = True
            TriMesh.__init__(self, self.get_polydata_triangles(), self.get_polydata_vertices(), dtype=dtype, atol=atol, assert_args=assert_args)
        else:
            self.__polydata__ = None
            self.__polydata_is_up_to_date__ = False
            TriMesh.__init__(self, triangles, vertices, dtype=dtype, atol=atol, assert_args=assert_args)

    # set and get, add an to update bool
    def set_triangles(self, triangles):
        TriMesh.set_triangles(self, triangles)
        self.__polydata_is_up_to_date__ = False

    def set_vertices(self, vertices):
        TriMesh.set_vertices(self, vertices)
        self.__polydata_is_up_to_date__ = False

    # vtk polydata function
    # todo remove and fix the update normals
    def get_polydata(self, update_normal=False):
        if self.__polydata_is_up_to_date__ is False:
            self.update_polydata()
        if update_normal:
            self.update_normals()
        return self.__polydata__

    def update_polydata(self):
        self.__polydata__ = vtk.vtkPolyData()
        self.__polydata_is_up_to_date__ = True
        self.set_polydata_triangles(self.get_triangles())
        self.set_polydata_vertices(self.get_vertices())

    def get_polydata_triangles(self):
        vtk_polys = ns.vtk_to_numpy(self.get_polydata().GetPolys().GetData())
        assert((vtk_polys[::4] == 3).all())  # test if really triangle
        triangles = np.vstack([vtk_polys[1::4], vtk_polys[2::4], vtk_polys[3::4]]).T
        return triangles

    def get_polydata_vertices(self):
        return ns.vtk_to_numpy(self.get_polydata().GetPoints().GetData())

    def set_polydata_triangles(self, triangles):
        vtk_triangles = np.hstack(np.c_[np.ones(len(triangles)).astype(np.int) * 3, triangles])
        vtk_triangles = ns.numpy_to_vtkIdTypeArray(vtk_triangles, deep=True)
        vtk_cells = vtk.vtkCellArray()
        vtk_cells.SetCells(len(triangles), vtk_triangles)
        self.get_polydata().SetPolys(vtk_cells)

    def set_polydata_vertices(self, vertices):
        vtk_points = vtk.vtkPoints()
        vtk_points.SetData(ns.numpy_to_vtk(vertices, deep=True))
        self.get_polydata().SetPoints(vtk_points)

    # Normals
    def get_normals(self):
        vtk_normals = self.get_polydata().GetPointData().GetNormals()
        if vtk_normals is None:
            return None
        else:
            return ns.vtk_to_numpy(vtk_normals)

    def set_normals(self, normals):
        vtk_normals = ns.numpy_to_vtk(normals, deep=True)
        self.get_polydata().GetPointData().SetNormals(vtk_normals)

    # Colors
    def get_colors(self):
        vtk_colors = self.get_polydata().GetPointData().GetScalars()
        if vtk_colors is None:
            return None
        else:
            return ns.vtk_to_numpy(vtk_colors)

    def set_colors(self, colors):
        # Colors are [0,255] RGB for each points
        vtk_colors = ns.numpy_to_vtk(colors, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
        vtk_colors.SetNumberOfComponents(3)
        vtk_colors.SetName("RGB")
        self.get_polydata().GetPointData().SetScalars(vtk_colors)

# Updates :
    def update_normals(self):
        normals_gen = self.polydata_input(vtk.vtkPolyDataNormals())
        normals_gen.ComputePointNormalsOn()
        normals_gen.ComputeCellNormalsOn()
        normals_gen.SplittingOff()
        #normals_gen.FlipNormalsOn()
        #normals_gen.ConsistencyOn()
        #normals_gen.AutoOrientNormalsOn()
        normals_gen.Update()

        # memory leak if we use :  self.polydata = normals_gen.GetOutput()
        # dont copy the polydata because memory leak
        vtk_normals = normals_gen.GetOutput().GetPointData().GetNormals()
        self.get_polydata().GetPointData().SetNormals(vtk_normals)

    def update(self):
        if vtk.VTK_MAJOR_VERSION <= 5:
            self.get_polydata().Update()
        else:
            self.update_polydata()

# Display :
    def get_vtk_polymapper(self):
        poly_mapper = self.polydata_input(vtk.vtkPolyDataMapper())
        poly_mapper.ScalarVisibilityOn()
        poly_mapper.InterpolateScalarsBeforeMappingOn()
        poly_mapper.Update()
        poly_mapper.StaticOn()
        return poly_mapper

    def get_vtk_actor(self, light=(0.1, 0.15, 0.05)):
        poly_mapper = self.get_vtk_polymapper()
        actor = vtk.vtkActor()
        actor.SetMapper(poly_mapper)
        # actor.GetProperty().SetRepresentationToWireframe()
        actor.GetProperty().BackfaceCullingOn()
        actor.GetProperty().SetInterpolationToPhong()
        # actor.GetProperty().SetInterpolationToFlat()

        actor.GetProperty().SetAmbient(light[0])  # .3
        actor.GetProperty().SetDiffuse(light[1])  # .3
        actor.GetProperty().SetSpecular(light[2])  # .3

        return actor

    def display(self, display_name="trimesh", size=(400, 400), light=(0.1, 0.15, 0.05), background=(0.0,0.0,0.0), png_magnify=1):
        # from dipy.fvtk
        renderer = vtk.vtkRenderer()
        renderer.AddActor(self.get_vtk_actor(light))
        renderer.ResetCamera()
        renderer.SetBackground(background)
        window = vtk.vtkRenderWindow()
        window.AddRenderer(renderer)
        # window.SetAAFrames(6)
        window.SetWindowName(display_name)
        window.SetSize(size[0], size[1])
        style = vtk.vtkInteractorStyleTrackballCamera()
        iren = vtk.vtkRenderWindowInteractor()
        iren.SetRenderWindow(window)
        picker = vtk.vtkCellPicker()
        iren.SetPicker(picker)

        def key_press(obj, event):
            key = obj.GetKeySym()
            if key == 's' or key == 'S':
                print('Saving image...')
                renderLarge = vtk.vtkRenderLargeImage()
                if vtk.VTK_MAJOR_VERSION <= 5:
                    renderLarge.SetInput(renderer)
                else:
                    renderLarge.SetInputData(renderer)
                renderLarge.SetMagnification(png_magnify)
                renderLarge.Update()
                writer = vtk.vtkPNGWriter()
                writer.SetInputConnection(renderLarge.GetOutputPort())
                writer.SetFileName('trimesh_save.png')
                writer.Write()
                print('Look for trimesh_save.png in your current working directory.')

        iren.AddObserver('KeyPressEvent', key_press)
        iren.SetInteractorStyle(style)
        iren.Initialize()
        picker.Pick(85, 126, 0, renderer)
        window.Render()
        iren.Start()
        # window.RemoveAllObservers()
        window.RemoveRenderer(renderer)
        renderer.SetRenderWindow(None)

    # Input for mapper or polydata
    def polydata_input(self, vtk_object):
        if vtk.VTK_MAJOR_VERSION <= 5:
            vtk_object.SetInput(self.get_polydata())
        else:
            vtk_object.SetInputData(self.get_polydata())
        vtk_object.Update()
        return vtk_object

    def save(self, file_name):
        self.update()
        vtk_u.save_polydata(self.__polydata__, file_name)

    