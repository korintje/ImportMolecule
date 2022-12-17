# Author-korintje.
# Description-Import molecule

import adsk
import os, sys, math, glob, configparser, traceback, subprocess
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# Global instances
core = adsk.core
fusion = adsk.fusion
app = core.Application.get()
if app:
    ui = app.userInterface
    product = app.activeProduct
    design = fusion.Design.cast(product)

# Global variables
handlers = []
settings = {}
radii_settings = {}

# Global constants
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
RESOURCE_DIR = os.path.join(CURRENT_DIR, 'resources')
DEFAULT_SETNAMES = {
    "name": "Molecule",
    "atom_enabled": True,
    "radii": "Uniform",
    "colors": "Default",
    "atom_scale": 1.0,
    "bond_radius": 0.1,
    "bond_enabled": False,
    "use_slab": False,
    "mirror_indices": [0, 0, 1],
    "thickness": 1,
    "repeat_numbers": [1, 1, 1],
    "modeling_mode": "Direct",
}

ANGLE_2PI = core.ValueInput.createByReal(2 * math.pi)
TLSTYLE = core.DropDownStyles.TextListDropDownStyle
NBFEATURE = fusion.FeatureOperations.NewBodyFeatureOperation
ALL_ELEMENTS = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", 
    "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf",
    "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"
]

# Appearance config
_cfg = configparser.ConfigParser()
_cfg.read(os.path.join(RESOURCE_DIR, "appearances"))
_options = _cfg["options"]
DEFAULT_APPEARANCE_NAME = _options.get("default_value")
APPEARANCE_LIB_ID = _options.get("appearance_lib_id")
APPEARANCE_IDS = _cfg["ids"]

# Try to import ASE module. If not exist, first install ASE and import it.
try:
    import ase.io
    import ase.build
    import ase.neighborlist
except:
    SCRIPTPATH = os.path.join(CURRENT_DIR, "get-pip.py")
    PYTHONPATH = sys.executable
    if PYTHONPATH.endswith("Fusion360.exe") or PYTHONPATH.endswith("Fusion360"):
        f360dirname = os.path.dirname(PYTHONPATH)
        PYTHONPATH = os.path.join(f360dirname, "Python", "python")
    ui.messageBox('Press OK to install required modules (Shown only at the first run)')
    try:
        code1 = subprocess.call([PYTHONPATH, "-m", "pip", "-V"])
        if str(code1) != "0":
            call1 = subprocess.check_call([PYTHONPATH, SCRIPTPATH])
    except:
        ui.messageBox(f'Failed to install pip:\n{call1}')
    try:
        call2 = subprocess.check_call([PYTHONPATH, "-m", "pip", "install", "--upgrade", "ase"])
    except:
        ui.messageBox(f'Failed to install ASE:\n{call2}')
    ui.messageBox("Required module installation has finished.")
    import ase.io
    import ase.build
    import ase.neighborlist


# Load a config to create drop down input
def create_inputs_from_config(inputs, configtype):
    settings[configtype] = {}
    setNameInput = inputs.addDropDownCommandInput(f"{configtype}SetName", f'{configtype} set', TLSTYLE)
    setting_fnames = glob.glob(f"{RESOURCE_DIR}/*.{configtype}")
    for fname in setting_fnames:
        config = configparser.ConfigParser()
        config.read(fname)
        options = config["options"]
        values = config["elements"]
        setting_name = options.get("name")
        default_value = options.get("default_value")
        settings[configtype][setting_name] = {}
        for element in ALL_ELEMENTS:
            value = values.get(element, default_value)
            settings[configtype][setting_name][element] = value
        if setting_name == DEFAULT_SETNAMES[configtype]:
            setNameInput.listItems.add(setting_name, True, "")
        else:
            setNameInput.listItems.add(setting_name, False, "")


# Create new component
def createNewComponent():
    rootComp = design.rootComponent
    allOccs = rootComp.occurrences
    newOcc = allOccs.addNewComponent(core.Matrix3D.create())
    return newOcc.component


# Execute command handler
class MoleculeCommandExecuteHandler(core.CommandEventHandler):

    def __init__(self, atoms):
        super().__init__()
        self.atoms = atoms
    
    def notify(self, args):
        try:
            unitsMgr = app.activeProduct.unitsManager
            command = args.firingEvent.sender
            inputs = command.commandInputs
            molecule = Molecule(self.atoms)
            slabActivated = True
            for ipt in inputs:
                if ipt.id == "moleculeName":
                    molecule.moleculeName = ipt.value
                elif ipt.id == "atomEnabled":
                    molecule.atomEnabled = ipt.value
                elif ipt.id == "radiiSetName":
                    molecule.radiiSetName = ipt.selectedItem.name
                elif ipt.id == "colorsSetName":
                    molecule.colorsSetName = ipt.selectedItem.name
                elif ipt.id == "atomScale":
                    molecule.atomScale = ipt.value
                elif ipt.id == "bondRadius":
                    molecule.bondRadius = ipt.value
                elif ipt.id == "bondEnabled":
                    molecule.bondEnabled = ipt.value
                elif ipt.id == "useSlab":
                    molecule.useSlab = ipt.value
                    slabActivated = True if ipt.value else False
                elif ipt.id == "mirror_h":
                    molecule.mirrorIndices[0] = ipt.value
                    ipt.isEnabled = True if slabActivated else False
                elif ipt.id == "mirror_k":
                    molecule.mirrorIndices[1] = ipt.value
                    ipt.isEnabled = True if slabActivated else False
                elif ipt.id == "mirror_l":
                    molecule.mirrorIndices[2] = ipt.value
                    ipt.isEnabled = True if slabActivated else False
                elif ipt.id == "thickness":
                    molecule.thickness = ipt.value
                    ipt.isEnabled = True if slabActivated else False
                elif ipt.id == "repeat_a":
                    molecule.repeatNumbers[0] = ipt.value
                    ipt.isEnabled = True if slabActivated else False
                elif ipt.id == "repeat_b":
                    molecule.repeatNumbers[1] = ipt.value
                    ipt.isEnabled = True if slabActivated else False
                elif ipt.id == "repeat_c":
                    molecule.repeatNumbers[2] = ipt.value
                    ipt.isEnabled = True if slabActivated else False
                elif ipt.id == "appearance":
                    molecule.appearanceID = APPEARANCE_IDS[ipt.selectedItem.name]
                elif ipt.id == "modeling_mode":
                    molecule.modelingMode = ipt.selectedItem.name
                
            molecule.buildMoleculeWrapper()
            args.isValidResult = True

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Destroy command handler
class MoleculeCommandDestroyHandler(core.CommandEventHandler):

    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Command create handler
class MoleculeCommandCreatedHandler(core.CommandCreatedEventHandler):

    def __init__(self, atoms):
        super().__init__()
        self.atoms = atoms

    def notify(self, args):
        try:
            cmd = args.command
            cmd.isRepeatable = False

            # Register to Execute command
            onExecute = MoleculeCommandExecuteHandler(self.atoms)
            cmd.execute.add(onExecute)
            handlers.append(onExecute)

            # Register to ExecutePreview command
            onExecutePreview = MoleculeCommandExecuteHandler(self.atoms)
            cmd.executePreview.add(onExecutePreview)
            handlers.append(onExecutePreview)

            # Register to Destroy command
            onDestroy = MoleculeCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            handlers.append(onDestroy)

            # Define the inputs and groups
            inputs: core.CommandInputs = cmd.commandInputs
            molecularInputs = inputs.addGroupCommandInput("molecule", "Molecular settings")
            atomInputs = inputs.addGroupCommandInput("atom", "Atom settings")
            bondInputs = inputs.addGroupCommandInput("bond", "Bond settings")
            
            # Add inputs of molecular settings
            molecularInputs.children.addStringValueInput('moleculeName', 'molecular name', DEFAULT_SETNAMES["name"])
            
            # Add dropdown lists of atom settings
            atomInputs.children.addBoolValueInput("atomEnabled", "draw atom spheres", True, "", DEFAULT_SETNAMES["atom_enabled"])
            create_inputs_from_config(atomInputs.children, "radii")
            create_inputs_from_config(atomInputs.children, "colors")
            ks = ",".join(settings["radii"]["VDW"].keys())
            atomInputs.children.addFloatSpinnerCommandInput("atomScale", "atom scale", "", 0.1, 10, 0.1, DEFAULT_SETNAMES["atom_scale"])

            # Add inputs of bond settings
            bondInputs.children.addBoolValueInput("bondEnabled", "draw bonds", True, "", DEFAULT_SETNAMES["bond_enabled"])
            bondInputs.children.addFloatSpinnerCommandInput("bondRadius", "bond radius", "", 0.01, 100, 0.01, DEFAULT_SETNAMES["bond_radius"])

            # Add inputs of slab settings
            if any(self.atoms.get_pbc()):
                slabInputs = inputs.addGroupCommandInput("slab", "Slab settings")
                slabInputs.children.addBoolValueInput("useSlab", "Use slab", True, "", False)
                _h = slabInputs.children.addIntegerSpinnerCommandInput("mirror_h", "mirror index h", 0, 100, 1, DEFAULT_SETNAMES["mirror_indices"][0])
                _k = slabInputs.children.addIntegerSpinnerCommandInput("mirror_k", "mirror index k", 0, 100, 1, DEFAULT_SETNAMES["mirror_indices"][1])
                _l = slabInputs.children.addIntegerSpinnerCommandInput("mirror_l", "mirror index l", 0, 100, 1, DEFAULT_SETNAMES["mirror_indices"][2])
                _a = slabInputs.children.addIntegerSpinnerCommandInput("repeat_a", "repeat for x", 0, 100, 1, DEFAULT_SETNAMES["repeat_numbers"][0])
                _b = slabInputs.children.addIntegerSpinnerCommandInput("repeat_b", "repeat for y", 0, 100, 1, DEFAULT_SETNAMES["repeat_numbers"][1])
                _t = slabInputs.children.addIntegerSpinnerCommandInput("thickness", "repeat for z", 1, 100, 1, DEFAULT_SETNAMES["thickness"])
                # slabInputs.children.addIntegerSpinnerCommandInput("repeat_c", "repeat number c", 0, 100, 1, DEFAULT_SETNAMES["repeat_numbers"][2])
                for i in [_h, _k, _l, _t, _a, _b]:
                    i.isEnabled = False
            
            # Add inputs of other settings
            otherInputs = inputs.addGroupCommandInput("other", "Other settings")
            appearance_input = otherInputs.children.addDropDownCommandInput("appearance", "appearance", TLSTYLE)
            for appearance_name in APPEARANCE_IDS.keys():
                is_selected = True if appearance_name == DEFAULT_APPEARANCE_NAME else False
                appearance_input.listItems.add(appearance_name, is_selected)
            mode_input = otherInputs.children.addDropDownCommandInput("modeling_mode", "modeling mode", TLSTYLE)
            mode_input.listItems.add("Direct", True, "")
            mode_input.listItems.add("Parametric", False, "")

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Molecular model class
class Molecule:

    def __init__(self, atoms):
        self.atoms = atoms
        self._moleculeName = DEFAULT_SETNAMES["name"]
        self._atomEnabled = DEFAULT_SETNAMES["atom_enabled"]
        self._radiiSetName = DEFAULT_SETNAMES["radii"]
        self._colorsSetName = DEFAULT_SETNAMES["colors"]
        self._atomScale = DEFAULT_SETNAMES["atom_scale"]
        self._bondEnabled = DEFAULT_SETNAMES["bond_enabled"]
        self._bondRadius = DEFAULT_SETNAMES["bond_radius"]
        self._useSlab = DEFAULT_SETNAMES["use_slab"]
        self._mirrorIndices = DEFAULT_SETNAMES["mirror_indices"]
        self._thickness = DEFAULT_SETNAMES["thickness"]
        self._repeatNumbers = DEFAULT_SETNAMES["repeat_numbers"]
        self._appearanceID = APPEARANCE_IDS[DEFAULT_APPEARANCE_NAME]
        self._modelingMode = DEFAULT_SETNAMES["modeling_mode"]

    @property
    def moleculeName(self):
        return self._moleculeName
    @moleculeName.setter
    def moleculeName(self, value):
        self._moleculeName = value

    @property
    def atomEnabled(self):
        return self._atomEnabled
    @atomEnabled.setter
    def atomEnabled(self, value):
        self._atomEnabled = value

    @property
    def radiiSetName(self):
        return self._radiiSetName
    @radiiSetName.setter
    def radiiSetName(self, value):
        self._radiiSetName = value

    @property
    def colorsSetName(self):
        return self._colorsSetName
    @colorsSetName.setter
    def colorsSetName(self, value):
        self._colorsSetName = value

    @property
    def atomScale(self):
        return self._atomScale
    @atomScale.setter
    def atomScale(self, value):
        self._atomScale = value

    @property
    def bondEnabled(self):
        return self._bondEnabled
    @bondEnabled.setter
    def bondEnabled(self, value):
        self._bondEnabled = value

    @property
    def bondRadius(self):
        return self._bondRadius
    @bondRadius.setter
    def bondRadius(self, value):
        self._bondRadius = value

    @property
    def useSlab(self):
        return self._useSlab
    @useSlab.setter
    def useSlab(self, value):
        self._useSlab = value

    @property
    def mirrorIndices(self):
        return self._mirrorIndices
    @mirrorIndices.setter
    def mirrorIndices(self, value):
        self._mirrorIndices = value

    @property
    def thickness(self):
        return self._thickness
    @thickness.setter
    def thickness(self, value):
        self._thickness = value

    @property
    def repeatNumbers(self):
        return self._repeatNumbers
    @repeatNumbers.setter
    def repeatNumbers(self, value):
        self._repeatNumbers = value

    @property
    def appearanceID(self):
        return self._appearanceID
    @appearanceID.setter
    def appearanceID(self, value):
        self._appearanceID = value

    @property
    def modelingMode(self):
        return self._modelingMode
    @modelingMode.setter
    def modelingMode(self, value):
        self._modelingMode = value

    def buildMoleculeWrapper(self):
        try:
            if self.useSlab and any(self.atoms.get_pbc()):
                slab = ase.build.surface(
                    self.atoms,
                    tuple(self.mirrorIndices), 
                    self.thickness
                )
                repeated_slab = slab.repeat(tuple(self.repeatNumbers))  
                if self.modelingMode == "Parametric":
                    self.buildMolecule(repeated_slab)
                else:
                    self.buildMoleculeDirect(repeated_slab)
            else:
                if self.modelingMode == "Parametric":
                    self.buildMolecule(self.atoms)
                else:
                    self.buildMoleculeDirect(self.atoms)
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))            

    def buildMoleculeDirect(self, target_atoms):
        try:

            # Get material and appearance libraries
            materialLibs = app.materialLibraries
            # presetMaterials = materialLibs.itemById(MATERIAL_LIB_ID).materials
            # material = presetMaterials.itemById(DEFAULT_MATERIAL_ID)
            presetAppearances = materialLibs.itemById(APPEARANCE_LIB_ID).appearances
            favoriteAppearances = design.appearances

            # Set direct mode
            design.designType = adsk.fusion.DesignTypes.DirectDesignType

            # Create new component
            comp = createNewComponent()
            comp.name = self.moleculeName
            if comp is None:
                ui.messageBox('New component failed to create', 'New Component Failed')
                return
            bodies = comp.bRepBodies

            # Create progress dialog.
            progressDialog = ui.createProgressDialog()
            progressDialog.cancelButtonText = 'Cancel'
            progressDialog.isBackgroundTranslucent = False
            progressDialog.isCancelButtonShown = True
            atom_count = len(target_atoms.symbols)
            progressDialog.show('Creating molecules...', '%v/%m atoms done', 0, atom_count, 1)

            # Load settings
            radii_setting = settings["radii"][self.radiiSetName]
            colors_setting = settings["colors"][self.colorsSetName]
            element_counts = {}
            
            # Get neighbor atom list
            neighborlist = ase.neighborlist.build_neighbor_list(target_atoms, bothways=True, self_interaction=False)

            # TemporaryBRepManager
            tmpBrep = adsk.fusion.TemporaryBRepManager.get()

            for idx, (element, position) in enumerate(zip(target_atoms.symbols, target_atoms.positions)):

                # Bodies created in the current loop
                current_bodies = []

                # Element count, radius
                if not element_counts.get(element):
                    element_counts[element] = 1
                else:
                    element_counts[element] += 1
                element_count = element_counts[element]

                # Create atom sphere
                if self.atomEnabled:
                    origin = core.Point3D.create(*position)
                    radius = float(radii_setting[element]) / 100 * self.atomScale
                    tmpAtomBody = tmpBrep.createSphere(origin, radius)
                    atomBody = bodies.add(tmpAtomBody)
                    atomBody.name = element + str(element_count)
                    current_bodies.append(atomBody)

                # Create half bonds
                sweepBodies = []
                if self.bondEnabled and self.bondRadius > 0.0:
                    indices, offsets = neighborlist.get_neighbors(idx)
                    for j, offset in zip(indices, offsets):
                        neighbor_position = target_atoms.positions[j] + offset @ target_atoms.get_cell()
                        midpoint = (position + neighbor_position) / 2
                        tmpBondBody = tmpBrep.createCylinderOrCone(
                            core.Point3D.create(*position),
                            self.bondRadius,
                            core.Point3D.create(*midpoint),
                            self.bondRadius
                        )
                        bondBody = bodies.add(tmpBondBody)
                        bondBody.name = "Bond_" + element + str(element_count) + "-" + str(j + 1)
                        current_bodies.append(bondBody)

                # Set appearance
                element_color_name = f'{element}_color'
                color = [int(rgb.strip()) for rgb in colors_setting[element].strip().split(",")]
                try:
                    elementColor = favoriteAppearances.itemByName(element_color_name)
                except:
                    elementColor = None
                if not elementColor:
                    baseColor = presetAppearances.itemById(self.appearanceID)
                    newColor = favoriteAppearances.addByCopy(baseColor, element_color_name)
                    colorProp = core.ColorProperty.cast(newColor.appearanceProperties.itemById('opaque_albedo'))
                    colorProp.value = core.Color.create(*color, 0)
                    elementColor = favoriteAppearances.itemByName(element_color_name)
                for body in current_bodies:
                    # body.material = material
                    body.appearance = elementColor

                # Update / Cancel progress
                if progressDialog.wasCancelled:
                    break
                progressDialog.progressValue = idx + 1
            
            # Hide the progress dialog at the end.
            progressDialog.hide()

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))     

    def buildMolecule(self, target_atoms):
        try:

            # Set parametric mode
            design.designType = adsk.fusion.DesignTypes.ParametricDesignType

            # Get material and appearance libraries
            materialLibs = app.materialLibraries
            # presetMaterials = materialLibs.itemById(MATERIAL_LIB_ID).materials
            # material = presetMaterials.itemById(DEFAULT_MATERIAL_ID)
            presetAppearances = materialLibs.itemById(APPEARANCE_LIB_ID).appearances
            favoriteAppearances = design.appearances

            # global newComp
            newComp = createNewComponent()
            newComp.name = self.moleculeName
            if newComp is None:
                ui.messageBox('New component failed to create', 'New Component Failed')
                return

            # Create progress dialog.
            progressDialog = ui.createProgressDialog()
            progressDialog.cancelButtonText = 'Cancel'
            progressDialog.isBackgroundTranslucent = False
            progressDialog.isCancelButtonShown = True
            atom_count = len(target_atoms.symbols)
            progressDialog.show('Creating molecules...', '%v/%m atoms done', 0, atom_count, 1)

            # Create a new sketch.
            sketches = newComp.sketches
            xyPlane = newComp.xYConstructionPlane
            radii_setting = settings["radii"][self.radiiSetName]
            colors_setting = settings["colors"][self.colorsSetName]
            feats = newComp.features
            revolves = feats.revolveFeatures
            element_counts = {}
               
            neighborlist = ase.neighborlist.build_neighbor_list(target_atoms, bothways=True, self_interaction=False)
            for idx, (element, position) in enumerate(zip(target_atoms.symbols, target_atoms.positions)):

                # Element count, radius
                if not element_counts.get(element):
                    element_counts[element] = 1
                else:
                    element_counts[element] += 1
                element_count = element_counts[element]
                
                # Add a sketch
                sketch = sketches.add(xyPlane)
                sketch.isComputeDeferred = False

                if self.atomEnabled:
                    # Draw a circle.
                    origin = core.Point3D.create(*position)
                    radius = float(radii_setting[element]) / 100 * self.atomScale
                    circle1 = sketch.sketchCurves.sketchCircles.addByCenterRadius(origin, radius)
                    
                    # Draw a line to use as the axis of revolution.
                    lines = sketch.sketchCurves.sketchLines
                    edge_0 = core.Point3D.create(position[0] + radius, position[1], position[2])
                    edge_1 = core.Point3D.create(position[0] - radius, position[1], position[2])
                    axisLine = lines.addByTwoPoints(edge_0, edge_1)

                    # Get the profile defined by the circle.
                    prof = sketch.profiles.item(0)

                    # Create an revolution input to be able to define the input needed for a revolution
                    revInput = revolves.createInput(prof, axisLine, NBFEATURE)
                    _result = revInput.setAngleExtent(False, ANGLE_2PI)

                    # Create the extrusion.
                    revolve = revolves.add(revInput)
                    body = revolve.bodies[0]
                    body.name = element + str(element_count)

                # Create half bonds
                sweepBodies = []
                if self.bondEnabled and self.bondRadius > 0.0:
                    indices, offsets = neighborlist.get_neighbors(idx)
                    for j, offset in zip(indices, offsets):

                        # Create a path of half bond
                        neighbor_position = target_atoms.positions[j] + offset @ target_atoms.get_cell()
                        midpoint = (position + neighbor_position) / 2
                        bondLine = sketch.sketchCurves.sketchLines.addByTwoPoints(
                            core.Point3D.create(*position),
                            core.Point3D.create(*midpoint)
                        )
                        bondPath = feats.createPath(bondLine)

                        # Create a parpendicular plane for half bond
                        planes = newComp.constructionPlanes
                        planeInput = planes.createInput()
                        planeInput.setByDistanceOnPath(bondPath, adsk.core.ValueInput.createByReal(0))
                        plane = planes.add(planeInput)

                        # Create a circle on a plane
                        sketch_2 = sketches.add(plane)
                        sketch_2.isComputeDeferred = False
                        center = plane.geometry.origin
                        center = sketch_2.modelToSketchSpace(center)
                        # ui.messageBox(str(self.bondRadius))
                        sketch_2.sketchCurves.sketchCircles.addByCenterRadius(center, self.bondRadius)
                        profile = sketch_2.profiles[0]

                        # Create sweep
                        sweepFeats = feats.sweepFeatures
                        sweepInput = sweepFeats.createInput(profile, bondPath, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                        sweepInput.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
                        sweepFeat = sweepFeats.add(sweepInput)
                        sweepBody = sweepFeat.bodies[0]
                        sweepBody.name = "Bond_" + element + str(element_count) + "-" + str(j + 1)
                        sweepBodies.append(sweepBody)

                # Set appearance
                element_color_name = f'{element}_color'
                color = [int(rgb.strip()) for rgb in colors_setting[element].strip().split(",")]
                try:
                    elementColor = favoriteAppearances.itemByName(element_color_name)
                except:
                    elementColor = None
                if not elementColor:
                    baseColor = presetAppearances.itemById(self.appearanceID)
                    newColor = favoriteAppearances.addByCopy(baseColor, element_color_name)
                    colorProp = core.ColorProperty.cast(newColor.appearanceProperties.itemById('opaque_albedo'))
                    colorProp.value = core.Color.create(*color, 0)
                    elementColor = favoriteAppearances.itemByName(element_color_name)
                if self.atomEnabled:
                    # body.material = material
                    body.appearance = elementColor
                for sweepBody in sweepBodies:
                    # sweepBody.material = material
                    sweepBody.appearance = elementColor

                # Update / Cancel progress
                if progressDialog.wasCancelled:
                    break
                progressDialog.progressValue = idx + 1
            
            # Hide the progress dialog at the end.
            progressDialog.hide()

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Entry point of the script
def run(context):

    try:

        # Check design exiss
        if not design:
            ui.messageBox('It is not supported in current workspace.')
            return

        # Open target molecular file
        dlg = ui.createFileDialog()
        dlg.title = 'Open Molecular Strucure File'
        dlg.filter = 'Molecular structure format ( \
            *.gjf;*.mol;*.mol2;*.pdb;*.xyz;*.cif;*.gen;*.sdf;*.com;*.vasp \
        );;All Files (*.*)'
        if dlg.showOpen() != core.DialogResults.DialogOK :
            return
        filepath = dlg.filename
        # ext = os.path.splitext(filepath)[-1]
        atoms = ase.io.read(filepath)

        # Check the command exists or not
        commandDefinitions = ui.commandDefinitions
        cmdDef = commandDefinitions.itemById('Molecule')
        if not cmdDef:
            cmdDef = commandDefinitions.addButtonDefinition(
                'Molecule',
                'Create Molecule',
                'Create a molecule.',
                './resources'
            )

        # Register to commandCreated event
        onCommandCreated = MoleculeCommandCreatedHandler(atoms)
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)
        inputs = core.NamedValues.create()
        cmdDef.execute(inputs)
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
