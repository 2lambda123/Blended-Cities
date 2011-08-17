##@mainpage Blended Cities internal documentation
# v0.6 for Blender 2.5.8a
#
# this is the continuation of a project begun with 2.4x releases of blender :
#
# http://jerome.le.chat.free.fr/index.php/en/city-engine
#
# the version number starts after the last blended cities release for 2.49b \
# but this is tests stage for now (july 2011)

##@file
# main.py
# the main city class
# bpy.context.scene.city
# the file calls the other modules and holds the main city methods

# class_import is responsible for loading the builders classes and guis from the builder folder
# this id done now before the city main class to register
# in order to give pointers towards builders to the main class


import sys
import copy
import collections

import bpy
import blf
import mathutils
from mathutils import *

#from blended_cities.core.ui import *
#from blended_cities.core.class_import import *
from blended_cities.core.class_main import *
from blended_cities.core.common import *
from blended_cities.utils.meshes_io import *
from blended_cities.core.ui import *

## return the active builder classes as a list
# @return [ [class name1, class1], [class name2, class2], ... ]
def builderClass() :
    scene = bpy.context.scene
    city = scene.city
    buildersList = []
    for k in city.builders.keys() :
        if type(city.builders[k]) == list :
            dprint('found builder %s'%(k),2)
            builderCollection = eval('city.builders.%s'%k)
            buildersList.append([k,builderCollection])
    return buildersList


## bpy.context.scene.city
# main class, main methods. holds all the pointers to element collections
class BlendedCities(bpy.types.PropertyGroup) :
    elements = bpy.props.CollectionProperty(type=BC_elements)
    outlines = bpy.props.CollectionProperty(type=BC_outlines)
    groups = bpy.props.CollectionProperty(type=BC_groups)
    ui = bpy.props.PointerProperty(type=BC_City_ui)

    debuglevel = bpy.props.IntProperty(default=1)
    builders_info = {} # info about builder authoring, should be a collection too. usage, could use bl_info..
    path = bpy.utils.script_paths('addons/blended_cities/')[0]

    bc_go = bpy.props.BoolProperty()
    bc_go_once = bpy.props.BoolProperty()

    ## returns the class of a given class name
    def Class(self,builder='') :
        if builder == '' : builder='nones'
        if builder in ['outlines', 'elements','groups'] :
            return eval('self.%s'%builder)
        try :
            elmclass = eval('self.builders.%s'%builder)
            return elmclass
        except :
            dprint('class %s not found.'%builder)
            return False


    ## create several elements  in a row / update existing outlines (replace their attached builders)  in a row
    # @param what a list of outline object, 'selected' keyword, 
    # @builder the name of the builder class
    # @otl_ob True if the outline object already exists. example for stack, the otl object is generated by elementStack from its parent
    # @build True True if one want the builder object to be built right now
    # @return a list of [ bld, otl ] for each builded object (the new element in its class, and its outline)
    def elementAdd(self,what='selected',builder='', build_it=True) :
        # lists of outlines object given by user selection
        otl_objects = returnObject(what)
        if otl_objects == False :
            otl_objects = ['none']
            build_it = False
        dprint(otl_objects)
        # the outline object is not known yet. no build() then
        #if otl_ob == False : build = False
        new_elms = []
        for otl_object in otl_objects :

            if otl_object != 'none' :
                # a list os string was given
                #if type(otl_object) == str :
                #    otl_object = bpy.data.objects[otl_object]

                #  check if this object is already known
                elm, grp, otl = self.elementGet(otl_object,True)
            else : elm = grp = otl = False

            if elm :
                #  case when a builder object was selected/given rather than the outline object
                otl_object = otl.object()

            if otl_object == 'none' \
            or (type(otl_object.data) == bpy.types.Mesh) :

                dprint('** element add')

                # check if the class exist
                elmclass = self.Class(builder)
                if elmclass == False : return False, False                    

                #  create a new outline
                if otl == False :
                    otl = self.outlines.add()
                    otl.nameNew()
                    otl_elm = otl._add() # add it in Element
                    otl.type = 'user'
                    dprint(' created otl %s'%otl.name)
                #  or free and reuse existing (remove the previous builder from collections)
                else :
                    grp.remove()
                    otl_elm = otl.asElement()
                    dprint(' reuse otl %s'%otl.name)

                #if otl_ob and builder != 'none' :
                if otl_object != 'none' :
                    otl_elm.pointer = str(otl_object.as_pointer())
                    otl.dataRead()
                    dprint(' otl object linked and red')
                else :
                    otl_elm.pointer = '-1'  # todo : spawn a primitive of the elm class
                    dprint(' no otl object yet')

                grp = otl.groupAdd(builder)
                dprint('  group is %s'%grp.name)

                # link parent and child
                # don't build if child element, the caller function will handle that, 
                # depending on other factors (object parenting ? build above existing ? deform outline ? etc)
                # it depends on the builder methods and where the caller want to locate the child 
                if build_it : #otl_ob :
                    #new.build()
                    grp.build()
                #else :
                #    otl.attached = builder if builder else 'none'
                #    new = False
                new_elms.append([grp, otl])
                dprint('** element add done')
        return new_elms


    ## stack several new elements on different outlines in a row
    # @param what a list of object or the keyword 'selected'
    # @builder the name of the builder class
    # @return a list of [ bld, otl ] for each builded object (the new element in its class, and its outline)
    def elementStack(self,what='selected',builder='buildings'):
        if what == 'selected' :
            parent_objects = bpy.context.selected_objects
        else :
            otl_objects = what
        new_elms = []
        for object in parent_objects :
            if type(object.data) == bpy.types.Mesh :
                bld_parent, otl_parent = self.elementGet(object)
                print('stacking over %s'%bld_parent.name)
                bld_child, otl_child = bld_parent.stack(False,builder)
                new_elms.append([bld_child, otl_child])
        return new_elms


    def groupAdd(self,what='selected',builder='nones'):
        dprint('* city.groupAdd')
        objs = returnObject(what)
        new_grps = []
        for ob in objs :
            print('object %s'%(ob.name))
            elm = self.elementGet(ob)
            if elm.className(False) == 'outlines' :
                otl = elm.inClass(False)
                grp = otl.groupAdd(builder)
                print('  added group %s'%(grp.name))
                new_grps.append(grp.name)
                grp.build()
        return new_grps


    def groupRemove(self, what='selected', rem_self=True, rem_elements=True, rem_objects=True, rem_childs=True):
        dprint('* city.groupRemove')
        objs = returnObject(what)
        del_grps = []
        for ob in objs :
            print('object %s'%(ob.name))
            elm = self.elementGet(ob)
            if elm.className(False) != 'outlines' :
                grp = elm.asGroup()
                print('remove %s'%(grp.name))
                del_grps.append(grp.name)
                grp.remove(rem_self, rem_elements, rem_objects, rem_childs)
        return del_grps


    ## remove selected outlines / parent outlines of selected objects
    # remove an existing element given an object or an element of any kind
    # will only let the outline object
    def outlineRemove(self,what='active', rem_self=True, rem_elements=True, rem_objects=True, rem_childs=True):
        dprint('* city.outlineRemove')
        objs = returnObject(what)
        del_objs = []
        for object in objs :
            #print('  'object.name,type(object.data))
            #if type(object.data) == bpy.types.Mesh :
            elm, grp, otl = self.elementGet(object,True)
            if elm :
                del_objs.append(otl.name)
                print('  removing outline %s (%s was selected)'%(otl.name,object.name))
                otl.remove(rem_self, rem_elements, rem_objects, rem_childs)

        return del_objs

    ## in [list of objects], remove builder x
    def builderRemove(self) :
        pass

    ## given an object or its name, returns the builder and the outline
    # @param ob (default False) object or object name. return active by default
    # @param inclass (default True) False : returns the Element only or False if not found.
    # @return [ bld, otl ] (the new element in its class, and its outline). [False,False] if not an element. [None,None] if object does not exist
    def elementGet(self,ob='active',detail=False) :
        ob = returnObject(ob)
        if ob == [] : return [None,None,None] if detail else None
        # seek
        pointer = str(ob[0].as_pointer())
        for elm in self.elements :
            if elm.pointer == pointer :
                if detail == False : return elm
                #if elm.className(False) == 'outlines' :
                return [elm, elm.asGroup(), elm.asOutline()]
        # not found
        return [False,False,False] if detail else False


    ## clean everything, restore the defaults
    # configure also the modal (it won't if BC is enabled by default, for now must be started by hand with city.modalConfig() )
    def init(self) :
        #
        #city = bpy.data.scenes[0].city
        city = self
        # remove any attached object
        for elm in city.elements :
            if elm.collection != 'outlines' or elm.asOutline().parent != '' :
                ob = elm.object()
                if type(ob) == bpy.types.Object : wipeOutObject(ob)
        # clean all collections of elements 
        while len(city.elements) > 0 :
            city.elements.remove(0)
        while len(city.outlines) > 0 :
            city.outlines.remove(0)
        while len(city.groups) > 0 :
            city.groups.remove(0)
        for buildname, buildclass in builderClass() :
            while len(buildclass) > 0 :
                buildclass.remove(0)

        # define default value
        city.modalConfig()
        bpy.context.scene.unit_settings.system = 'METRIC'


    ## rebuild everything from the collections (TO COMPLETE)
    # should support criterias filters etc like list should also
    # @return [ bld, otl ] (the element in its class, and its outline).
    def build(self,what='all', builder='all') :
        objs = []
        dprint('\n** BUILD ALL\n')
        for grp in self.groups :
            grp.build()
            objs.append([grp, grp.Parent()])
        return objs

    ## list all or part of the elements, filters, etc.., show parented element
    # should be able to generate a selection of elm in the ui,
    # in a search panel (TO COMPLETE)
    def list(self,what='all', builder='all') :
        elm_as_group = 0
        print('element list :\n--------------')
        def childsIter(otl,tab) :
            elm = otl.Childs(0)
            while elm :
                bld = elm.asBuilder()
                objs = bld.object()

                if type(objs) == bpy.types.Object : obn = 'built'
                elif objs : obn = 'group of %s objects'%(len(objs))
                else : obn = 'not built'
                print('%s : %s'%(bld.name,obn))
                if 'group' in obn :
                    for ob in objs : print('    %s'%ob.name)
                childsIter(elm,tab + '    ')
                elm = elm.Next()

        for otl in self.outlines :
            if otl.parent : continue
            print('* %s :\n'%otl.name)
            display(otl)
            '''
            bld = otl.asBuilder()
            objs = bld.object()
            
            if type(objs) == bpy.types.Object : obn = 'built'
            elif objs : obn = 'group of %s objects'%(len(objs))
            else : obn = 'not built'
            print('%s : %s'%(bld.name,obn))
            if 'group' in obn :
                for ob in objs : print('    %s'%ob.name)
            childsIter(otl,'    ')
            '''
        print('collections check :\n-------')
        total = len(self.elements) - elm_as_group
        print('%s elements :'%(total))
        print('outlines : %s'%(len(self.outlines)))
        count = len(self.outlines)
        bldclass = builderClass()
        for buildname,buildclass in bldclass :
            print('%s : %s'%(buildname,len(buildclass)))
            count += len(buildclass)
        if count != total : print("I've got a problem... %s / %s"%(count,total))


    ## modal configuration of script events
    def modalConfig(self) :
        mdl = bpy.context.window_manager.modal
        mdl.func = 'bpy.context.scene.city.modal(self,context,event)'


    ## the HUD function called from script events (TO DO)
    def hud() :
        pass


    ## the modal function called from script events (TO DO)
    def modal(self,self_mdl,context,event) :
            dprint('modal')
            if bpy.context.mode == 'OBJECT' and \
            len(bpy.context.selected_objects) == 1 and \
            type(bpy.context.active_object.data) == bpy.types.Mesh :
                elm,otl = self.elementGet(bpy.context.active_object)
                #if elm : elm.build(True)
                if elm : self.groups.build(elm)
            '''
                if elm.className() == 'buildings' or elm.peer().className() == 'buildings' :
                    dprint('rebuild')
                    if elm.className() == 'buildings' :
                        blg = elm
                    else :
                        blg = elm.peer()
                    dprint('rebuild')
                    blg.build(True)

            if event.type in ['TAB','SPACE'] :
                self.go_once = True

            if event.type in ['G','S','R'] :
                self.go=False
                
                if bpy.context.mode == 'OBJECT' and \
                len(bpy.context.selected_objects) == 1 and \
                type(bpy.context.active_object.data) == bpy.types.Mesh :
                    elm = self.elementGet(bpy.context.active_object)
                    if elm : self.go=True

            elif event.type in ['ESC','LEFTMOUSE','RIGHTMOUSE'] :
                    self.go=False
                    self.go_once=False
                    #dprint('modal paused.')
                    #mdl.log = 'paused.'
                    #context.region.callback_remove(self._handle)

            if event.type == 'TIMER' and (self.go or self.go_once) :
                        #self_mdl.log = 'updating...'

                        #dprint('event %s'%(event.type))
                        elm = self.elementGet(bpy.context.active_object)
                        #dprint('modal acting')

                        if elm.className() == 'buildings' or elm.peer().className() == 'buildings' :
                            if elm.className() == 'buildings' :
                                blg = elm
                            else :
                                blg = elm.peer()
                            dprint('rebuild')
                            blg.build(True)
            #bpy.ops.object.select_name(name=self.name)
                        self.go_once = False
                        #if self.go == False : mdl.log = 'paused.'
            '''


# register_class() for BC_builders and builders classes are made before
# the BlendedCities definition class_import
# else every module is register here
def register() :
    # operators
    pass

def unregister() :
    pass
if __name__ == "__main__" :
    dprint('B.C. wip')
    register()