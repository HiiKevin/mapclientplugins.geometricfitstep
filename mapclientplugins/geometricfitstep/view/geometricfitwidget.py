"""
User interface for github.com/ABI-Software/scaffoldfitter
"""
from PySide2 import QtCore, QtGui, QtWidgets

from mapclientplugins.geometricfitstep.utils.zinc_utils import field_is_managed_real_1_to_3_components
from mapclientplugins.geometricfitstep.view.ui_geometricfitwidget import Ui_GeometricFitWidget
from opencmiss.maths.vectorops import dot, magnitude, mult, normalize, sub

from opencmiss.utils.zinc.field import field_is_managed_coordinates, field_is_managed_group
from opencmiss.zinc.field import Field
from scaffoldfitter.fitterstepalign import FitterStepAlign
from scaffoldfitter.fitterstepconfig import FitterStepConfig
from scaffoldfitter.fitterstepfit import FitterStepFit


def QLineEdit_parseVector3(lineedit):
    """
    Return 3 component real vector as list from comma separated text in QLineEdit widget
    or None if invalid.
    """
    try:
        text = lineedit.text()
        values = [ float(value) for value in text.split(",") ]
        if len(values) == 3:
            return values
    except:
        pass
    return None


def QLineEdit_parseVectors(lineedit):
    """
    Return one or more component real vector as list from comma separated text in QLineEdit widget
    or None if invalid.
    """
    try:
        text = lineedit.text()
        values = [ float(value) for value in text.split(",") ]
        return values
    except:
        pass
    return None


def QLineEdit_parseRealNonNegative(lineedit):
    """
    Return non-negative real value from line edit text, or negative if failed.
    """
    try:
        value = float(lineedit.text())
        if value >= 0.0:
            return value
    except:
        pass
    return -1.0


class GeometricFitWidget(QtWidgets.QWidget):
    """
    User interface for github.com/ABI-Software/scaffoldfitter
    """

    def __init__(self, model, parent=None):
        """
        """
        super(GeometricFitWidget, self).__init__(parent)
        self._ui = Ui_GeometricFitWidget()
        self._ui.setupUi(self)
        self._ui.alignmentsceneviewerwidget.setContext(model.getContext())
        self._ui.alignmentsceneviewerwidget.setModel(model)
        self._model = model
        self._fitter = self._model.getFitter()
        self._region = self._fitter.getRegion()
        self._scene = self._region.getScene()
        self._currentFitterStep = self._fitter.getInitialFitterStepConfig()  # always exists
        self._ui.alignmentsceneviewerwidget.graphicsInitialized.connect(self._graphicsInitialized)
        self._callback = None
        self._setupConfigWidgets()
        self._setupGroupSettingWidgets()
        self._updateGeneralWidgets()
        self._updateDisplayWidgets()
        self._makeConnections()

    def _graphicsInitialized(self):
        """
        Callback for when SceneviewerWidget is initialised
        """
        self._sceneChanged()
        sceneviewer = self._ui.alignmentsceneviewerwidget.getSceneviewer()
        if sceneviewer is not None:
            sceneviewer.setTransparencyMode(sceneviewer.TRANSPARENCY_MODE_SLOW)
            self._autoPerturbLines()
            sceneviewer.viewAll()

    def _sceneChanged(self):
        """
        Set custom scene from model.
        """
        sceneviewer = self._ui.alignmentsceneviewerwidget.getSceneviewer()
        if sceneviewer is not None:
            self._model.createGraphics()
            sceneviewer.setScene(self._model.getScene())
            self._refreshGraphics()
            groupName = self._getGroupSettingsGroupName()
            if groupName:
                self._model.setSelectHighlightGroupByName(groupName)

    def _refreshGraphics(self):
        """
        Autorange spectrum and force redraw of graphics.
        """
        self._model.autorangeSpectrum()

    def _makeConnections(self):
        self._makeConnectionsGeneral()
        self._makeConnectionsDisplay()
        self._makeConnectionsGroup()
        self._makeConnectionsConfig()
        self._makeConnectionsAlign()
        self._makeConnectionsFit()

    def registerDoneExecution(self, callback):
        self._callback = callback

    def _autoPerturbLines(self):
        """
        Enable scene viewer perturb lines iff solid surfaces are drawn with lines.
        Call whenever lines, surfaces or translucency changes
        """
        sceneviewer = self._ui.alignmentsceneviewerwidget.getSceneviewer()
        if sceneviewer is not None:
            sceneviewer.setPerturbLinesFlag(self._model.needPerturbLines())

# === general widgets ===

    def _makeConnectionsGeneral(self):
        self._ui.stepsAddAlign_pushButton.clicked.connect(self._stepsAddAlignClicked)
        self._ui.stepsAddConfig_pushButton.clicked.connect(self._stepsAddConfigClicked)
        self._ui.stepsAddFit_pushButton.clicked.connect(self._stepsAddFitClicked)
        self._ui.stepsDelete_pushButton.clicked.connect(self._stepsDeleteClicked)
        self._ui.steps_listView.clicked[QtCore.QModelIndex].connect(self._stepsListItemClicked)
        self._ui.done_pushButton.clicked.connect(self._doneButtonClicked)
        self._ui.stdViews_pushButton.clicked.connect(self._stdViewsButtonClicked)
        self._ui.viewAll_pushButton.clicked.connect(self._viewAllButtonClicked)
        self._ui.next_pushButton.clicked.connect(self._nextButtonClicked)

    def _updateGeneralWidgets(self):
        self._ui.identifier_label.setText("Identifier:  " + self._model.getIdentifier())
        self._buildStepsList()

    def _stepsAddAlignClicked(self):
        """
        Add a new align step.
        """
        self._currentFitterStep = FitterStepAlign()
        self._fitter.addFitterStep(self._currentFitterStep)  # Future: , lastFitterStep
        self._buildStepsList()

    def _stepsAddConfigClicked(self):
        """
        Add a new config step.
        """
        self._currentFitterStep = FitterStepConfig()
        self._fitter.addFitterStep(self._currentFitterStep)  # Future: , lastFitterStep
        self._buildStepsList()

    def _stepsAddFitClicked(self):
        """
        Add a new fit step.
        """
        self._currentFitterStep = FitterStepFit()
        self._fitter.addFitterStep(self._currentFitterStep)  # Future: , lastFitterStep
        self._buildStepsList()

    def runToStep(self, endStep):
        """
        Run fitter steps up to specified end step.
        """
        fitterSteps = self._fitter.getFitterSteps()
        endIndex = fitterSteps.index(endStep)
        sceneChanged = self._fitter.run(endStep, self._model.getOutputModelFileNameStem())
        if sceneChanged:
            for index in range(endIndex + 1, len(fitterSteps)):
                self._refreshStepItem(fitterSteps[index])
            self._sceneChanged()
        else:
            for index in range(1, endIndex + 1):
                self._refreshStepItem(fitterSteps[index])
            self._refreshGraphics()

    def _stepsDeleteClicked(self):
        """
        Delete the currently selected step, except for initial config.
        Select next step after, or before if none.
        """
        assert self._currentFitterStep is not self._fitter.getInitialFitterStepConfig()
        if self._currentFitterStep.hasRun():
            # reload and run to step before current
            fitterSteps = self._fitter.getFitterSteps()
            index = fitterSteps.index(self._currentFitterStep)
            self._fitter.run(fitterSteps[index - 1])
            self._sceneChanged()
        self._currentFitterStep = self._fitter.removeFitterStep(self._currentFitterStep)
        self._buildStepsList()

    def _stepsListItemClicked(self, modelIndex):
        """
        Changes current step and possibly changes checked/run status.
        """
        model = modelIndex.model()
        item = model.itemFromIndex(modelIndex)
        step = item.data()
        if step != self._currentFitterStep:
           self._currentFitterStep = step
           self._updateFitterStepWidgets()
        isInitialConfig = step is self._fitter.getInitialFitterStepConfig()
        isChecked = True if isInitialConfig else (item.checkState() == QtCore.Qt.Checked)
        if step.hasRun() != isChecked:
            if isChecked:
                endStep = step
            else:
                fitterSteps = self._fitter.getFitterSteps()
                index = fitterSteps.index(step)
                endStep = fitterSteps[index - 1]
            self.runToStep(endStep)

    def _buildStepsList(self):
        """
        Fill the graphics list view with the list of graphics for current region/scene
        """
        self._stepsItems = QtGui.QStandardItemModel(self._ui.steps_listView)
        selectedIndex = None
        firstStep = True
        fitterSteps = self._fitter.getFitterSteps()
        for step in fitterSteps:
            name = None
            if isinstance(step, FitterStepAlign):
                name = "Align"
            elif isinstance(step, FitterStepConfig):
                name = "Config"
            elif isinstance(step, FitterStepFit):
                name = "Fit"
            else:
                assert False, "GeometricFitWidget.  Unknown FitterStep type"
            item = QtGui.QStandardItem(name)
            item.setData(step)
            item.setEditable(False)
            if firstStep:
                item.setCheckable(False)
                firstStep = False
            else:
                item.setCheckable(True)
                item.setCheckState(QtCore.Qt.Checked if step.hasRun() else QtCore.Qt.Unchecked)
            self._stepsItems.appendRow(item)
            if step == self._currentFitterStep:
                selectedIndex = self._stepsItems.indexFromItem(item)
        self._ui.steps_listView.setModel(self._stepsItems)
        self._ui.steps_listView.setCurrentIndex(selectedIndex)
        self._ui.steps_listView.show()
        self._updateFitterStepWidgets()

    def _refreshStepItem(self, step):
        """
        Update check state and selection of step in steps list view.
        :param stepIndex: Row index of item in step items.
        """
        index = self._fitter.getFitterSteps().index(step)
        item = self._stepsItems.item(index)
        if step is not self._fitter.getInitialFitterStepConfig():
            item.setCheckState(QtCore.Qt.Checked if step.hasRun() else QtCore.Qt.Unchecked)
        if step == self._currentFitterStep:
            self._ui.steps_listView.setCurrentIndex(self._stepsItems.indexFromItem(item))

    def _updateFitterStepWidgets(self):
        """
        Update and display widgets for currentFitterStep
        """
        isInitialConfig = self._currentFitterStep == self._fitter.getInitialFitterStepConfig()
        isAlign = isinstance(self._currentFitterStep, FitterStepAlign)
        isConfig = isinstance(self._currentFitterStep, FitterStepConfig)
        isFit = isinstance(self._currentFitterStep, FitterStepFit)
        if isAlign:
            self._updateAlignWidgets()
        elif isConfig:
            self._updateConfigWidgets()
        elif isFit:
            self._updateFitWidgets()
        self._ui.configInitial_groupBox.setVisible(isInitialConfig)
        self._ui.config_groupBox.setVisible(False)
        self._ui.align_groupBox.setVisible(isAlign)
        self._ui.fit_groupBox.setVisible(isFit)
        self._ui.groupSettings_groupBox.setVisible(not isAlign)
        self._ui.stepsDelete_pushButton.setEnabled(not isInitialConfig)

    def _doneButtonClicked(self):
        self._model.done()
        self._ui.dockWidget.setFloating(False)
        self._callback()

    def _nextButtonClicked(self):
        """Write the model connection codes here...
        """
        self._model.nextTime()
        self._fitter.load()

    def _stdViewsButtonClicked(self):
        sceneviewer = self._ui.alignmentsceneviewerwidget.getSceneviewer()
        if sceneviewer is not None:
            result, eyePosition, lookatPosition, upVector = sceneviewer.getLookatParameters()
            upVector = normalize(upVector)
            viewVector = sub(lookatPosition, eyePosition)
            viewDistance = magnitude(viewVector)
            viewVector = normalize(viewVector)
            viewX = dot(viewVector, [ 1.0, 0.0, 0.0 ])
            viewY = dot(viewVector, [ 0.0, 1.0, 0.0 ])
            viewZ = dot(viewVector, [ 0.0, 0.0, 1.0 ])
            upX = dot(upVector, [ 1.0, 0.0, 0.0 ])
            upY = dot(upVector, [ 0.0, 1.0, 0.0 ])
            upZ = dot(upVector, [ 0.0, 0.0, 1.0 ])
            if (viewZ < -0.999) and (upY > 0.999):
                # XY -> XZ
                viewVector = [ 0.0, 1.0, 0.0 ]
                upVector = [ 0.0, 0.0, 1.0 ]
            elif (viewY > 0.999) and (upZ > 0.999):
                # XZ -> YZ
                viewVector = [ -1.0, 0.0, 0.0 ]
                upVector = [ 0.0, 0.0, 1.0 ]
            else:
                # XY
                viewVector = [ 0.0, 0.0, -1.0 ]
                upVector = [ 0.0, 1.0, 0.0 ]
            eyePosition = sub(lookatPosition, mult(viewVector, viewDistance))
            sceneviewer.setLookatParametersNonSkew(eyePosition, lookatPosition, upVector)

    def _viewAllButtonClicked(self):
        self._ui.alignmentsceneviewerwidget.viewAll()

# === display widgets ===

    def _makeConnectionsDisplay(self):
        self._ui.displayAxes_checkBox.clicked.connect(self._displayAxesClicked)
        self._ui.displayMarkerDataPoints_checkBox.clicked.connect(self._displayMarkerDataPointsClicked)
        self._ui.displayMarkerDataNames_checkBox.clicked.connect(self._displayMarkerDataNamesClicked)
        self._ui.displayMarkerDataProjections_checkBox.clicked.connect(self._displayMarkerDataProjectionsClicked)
        self._ui.displayMarkerPoints_checkBox.clicked.connect(self._displayMarkerPointsClicked)
        self._ui.displayMarkerNames_checkBox.clicked.connect(self._displayMarkerNamesClicked)
        self._ui.displayDataPoints_checkBox.clicked.connect(self._displayDataPointsClicked)
        self._ui.displayDataProjections_checkBox.clicked.connect(self._displayDataProjectionsClicked)
        self._ui.displayDataProjectionPoints_checkBox.clicked.connect(self._displayDataProjectionPointsClicked)
        self._ui.displayNodePoints_checkBox.clicked.connect(self._displayNodePointsClicked)
        self._ui.displayNodeNumbers_checkBox.clicked.connect(self._displayNodeNumbersClicked)
        self._ui.displayNodeDerivativeLabelsD1_checkBox.clicked.connect(self._displayNodeDerivativeLabelsD1Clicked)
        self._ui.displayNodeDerivativeLabelsD2_checkBox.clicked.connect(self._displayNodeDerivativeLabelsD2Clicked)
        self._ui.displayNodeDerivativeLabelsD3_checkBox.clicked.connect(self._displayNodeDerivativeLabelsD3Clicked)
        self._ui.displayNodeDerivativeLabelsD12_checkBox.clicked.connect(self._displayNodeDerivativeLabelsD12Clicked)
        self._ui.displayNodeDerivativeLabelsD13_checkBox.clicked.connect(self._displayNodeDerivativeLabelsD13Clicked)
        self._ui.displayNodeDerivativeLabelsD23_checkBox.clicked.connect(self._displayNodeDerivativeLabelsD23Clicked)
        self._ui.displayNodeDerivativeLabelsD123_checkBox.clicked.connect(self._displayNodeDerivativeLabelsD123Clicked)
        self._ui.displayNodeDerivatives_checkBox.clicked.connect(self._displayNodeDerivativesClicked)
        self._ui.displayElementAxes_checkBox.clicked.connect(self._displayElementAxesClicked)
        self._ui.displayElementNumbers_checkBox.clicked.connect(self._displayElementNumbersClicked)
        self._ui.displayLines_checkBox.clicked.connect(self._displayLinesClicked)
        self._ui.displayLinesExterior_checkBox.clicked.connect(self._displayLinesExteriorClicked)
        self._ui.displaySurfaces_checkBox.clicked.connect(self._displaySurfacesClicked)
        self._ui.displaySurfacesExterior_checkBox.clicked.connect(self._displaySurfacesExteriorClicked)
        self._ui.displaySurfacesTranslucent_checkBox.clicked.connect(self._displaySurfacesTranslucentClicked)
        self._ui.displaySurfacesWireframe_checkBox.clicked.connect(self._displaySurfacesWireframeClicked)

    def _updateDisplayWidgets(self):
        """
        Update display widgets to display settings for model graphics display.
        """
        self._ui.displayAxes_checkBox.setChecked(self._model.isDisplayAxes())
        self._ui.displayMarkerDataPoints_checkBox.setChecked(self._model.isDisplayMarkerDataPoints())
        self._ui.displayMarkerDataNames_checkBox.setChecked(self._model.isDisplayMarkerDataNames())
        self._ui.displayMarkerDataProjections_checkBox.setChecked(self._model.isDisplayMarkerDataProjections())
        self._ui.displayMarkerPoints_checkBox.setChecked(self._model.isDisplayMarkerPoints())
        self._ui.displayMarkerNames_checkBox.setChecked(self._model.isDisplayMarkerNames())
        self._ui.displayDataPoints_checkBox.setChecked(self._model.isDisplayDataPoints())
        self._ui.displayDataProjections_checkBox.setChecked(self._model.isDisplayDataProjections())
        self._ui.displayDataProjectionPoints_checkBox.setChecked(self._model.isDisplayDataProjectionPoints())
        self._ui.displayNodePoints_checkBox.setChecked(self._model.isDisplayNodePoints())
        self._ui.displayNodeNumbers_checkBox.setChecked(self._model.isDisplayNodeNumbers())
        self._ui.displayNodeDerivativeLabelsD1_checkBox.setChecked(self._model.isDisplayNodeDerivativeLabels("D1"))
        self._ui.displayNodeDerivativeLabelsD2_checkBox.setChecked(self._model.isDisplayNodeDerivativeLabels("D2"))
        self._ui.displayNodeDerivativeLabelsD3_checkBox.setChecked(self._model.isDisplayNodeDerivativeLabels("D3"))
        self._ui.displayNodeDerivativeLabelsD12_checkBox.setChecked(self._model.isDisplayNodeDerivativeLabels("D12"))
        self._ui.displayNodeDerivativeLabelsD13_checkBox.setChecked(self._model.isDisplayNodeDerivativeLabels("D13"))
        self._ui.displayNodeDerivativeLabelsD23_checkBox.setChecked(self._model.isDisplayNodeDerivativeLabels("D23"))
        self._ui.displayNodeDerivativeLabelsD123_checkBox.setChecked(self._model.isDisplayNodeDerivativeLabels("D123"))
        self._ui.displayNodeDerivatives_checkBox.setChecked(self._model.isDisplayNodeDerivatives())
        self._ui.displayElementNumbers_checkBox.setChecked(self._model.isDisplayElementNumbers())
        self._ui.displayElementAxes_checkBox.setChecked(self._model.isDisplayElementAxes())
        self._ui.displayLines_checkBox.setChecked(self._model.isDisplayLines())
        self._ui.displayLinesExterior_checkBox.setChecked(self._model.isDisplayLinesExterior())
        self._ui.displaySurfaces_checkBox.setChecked(self._model.isDisplaySurfaces())
        self._ui.displaySurfacesExterior_checkBox.setChecked(self._model.isDisplaySurfacesExterior())
        self._ui.displaySurfacesTranslucent_checkBox.setChecked(self._model.isDisplaySurfacesTranslucent())
        self._ui.displaySurfacesWireframe_checkBox.setChecked(self._model.isDisplaySurfacesWireframe())

    def _displayAxesClicked(self):
        self._model.setDisplayAxes(self._ui.displayAxes_checkBox.isChecked())

    def _displayMarkerDataPointsClicked(self):
        self._model.setDisplayMarkerDataPoints(self._ui.displayMarkerDataPoints_checkBox.isChecked())

    def _displayMarkerDataNamesClicked(self):
        self._model.setDisplayMarkerDataNames(self._ui.displayMarkerDataNames_checkBox.isChecked())

    def _displayMarkerDataProjectionsClicked(self):
        self._model.setDisplayMarkerDataProjections(self._ui.displayMarkerDataProjections_checkBox.isChecked())

    def _displayMarkerPointsClicked(self):
        self._model.setDisplayMarkerPoints(self._ui.displayMarkerPoints_checkBox.isChecked())

    def _displayMarkerNamesClicked(self):
        self._model.setDisplayMarkerNames(self._ui.displayMarkerNames_checkBox.isChecked())

    def _displayDataPointsClicked(self):
        self._model.setDisplayDataPoints(self._ui.displayDataPoints_checkBox.isChecked())

    def _displayDataProjectionsClicked(self):
        self._model.setDisplayDataProjections(self._ui.displayDataProjections_checkBox.isChecked())

    def _displayDataProjectionPointsClicked(self):
        self._model.setDisplayDataProjectionPoints(self._ui.displayDataProjectionPoints_checkBox.isChecked())

    def _displayNodePointsClicked(self):
        self._model.setDisplayNodePoints(self._ui.displayNodePoints_checkBox.isChecked())

    def _displayNodeNumbersClicked(self):
        self._model.setDisplayNodeNumbers(self._ui.displayNodeNumbers_checkBox.isChecked())

    def _displayNodeDerivativesClicked(self):
        self._model.setDisplayNodeDerivatives(self._ui.displayNodeDerivatives_checkBox.isChecked())

    def _displayNodeDerivativeLabelsD1Clicked(self):
        self._model.setDisplayNodeDerivativeLabels("D1", self._ui.displayNodeDerivativeLabelsD1_checkBox.isChecked())

    def _displayNodeDerivativeLabelsD2Clicked(self):
        self._model.setDisplayNodeDerivativeLabels("D2", self._ui.displayNodeDerivativeLabelsD2_checkBox.isChecked())

    def _displayNodeDerivativeLabelsD3Clicked(self):
        self._model.setDisplayNodeDerivativeLabels("D3", self._ui.displayNodeDerivativeLabelsD3_checkBox.isChecked())

    def _displayNodeDerivativeLabelsD12Clicked(self):
        self._model.setDisplayNodeDerivativeLabels("D12", self._ui.displayNodeDerivativeLabelsD12_checkBox.isChecked())

    def _displayNodeDerivativeLabelsD13Clicked(self):
        self._model.setDisplayNodeDerivativeLabels("D13", self._ui.displayNodeDerivativeLabelsD13_checkBox.isChecked())

    def _displayNodeDerivativeLabelsD23Clicked(self):
        self._model.setDisplayNodeDerivativeLabels("D23", self._ui.displayNodeDerivativeLabelsD23_checkBox.isChecked())

    def _displayNodeDerivativeLabelsD123Clicked(self):
        self._model.setDisplayNodeDerivativeLabels("D123", self._ui.displayNodeDerivativeLabelsD123_checkBox.isChecked())

    def _displayElementAxesClicked(self):
        self._model.setDisplayElementAxes(self._ui.displayElementAxes_checkBox.isChecked())

    def _displayElementNumbersClicked(self):
        self._model.setDisplayElementNumbers(self._ui.displayElementNumbers_checkBox.isChecked())

    def _displayLinesClicked(self):
        self._model.setDisplayLines(self._ui.displayLines_checkBox.isChecked())
        self._autoPerturbLines()

    def _displayLinesExteriorClicked(self):
        self._model.setDisplayLinesExterior(self._ui.displayLinesExterior_checkBox.isChecked())

    def _displaySurfacesClicked(self):
        self._model.setDisplaySurfaces(self._ui.displaySurfaces_checkBox.isChecked())
        self._autoPerturbLines()

    def _displaySurfacesExteriorClicked(self):
        self._model.setDisplaySurfacesExterior(self._ui.displaySurfacesExterior_checkBox.isChecked())

    def _displaySurfacesTranslucentClicked(self):
        self._model.setDisplaySurfacesTranslucent(self._ui.displaySurfacesTranslucent_checkBox.isChecked())
        self._autoPerturbLines()

    def _displaySurfacesWireframeClicked(self):
        self._model.setDisplaySurfacesWireframe(self._ui.displaySurfacesWireframe_checkBox.isChecked())

# === group setting widgets ===

    def _setupGroupSettingWidgets(self):
        """
        Set up group setting widgets and display values from fitter object.
        """
        self._ui.groupSettings_fieldChooser.setRegion(self._region)
        self._ui.groupSettings_fieldChooser.setNullObjectName("-")
        self._ui.groupSettings_fieldChooser.setConditional(field_is_managed_group)
        self._ui.groupSettings_fieldChooser.setField(Field())

    def _makeConnectionsGroup(self):
        self._ui.groupSettings_fieldChooser.currentIndexChanged.connect(self._groupSettingsGroupChanged)
        self._ui.groupConfigCentralProjection_checkBox.clicked.connect(self._groupConfigCentralProjectionClicked)
        self._ui.groupConfigSetCentralProjection_checkBox.clicked.connect(self._groupConfigSetCentralProjectionClicked)
        self._ui.groupConfigDataProportion_checkBox.clicked.connect(self._groupConfigDataProportionClicked)
        self._ui.groupConfigDataProportion_lineEdit.editingFinished.connect(self._groupConfigDataProportionEntered)
        self._ui.groupFitDataWeight_checkBox.clicked.connect(self._groupFitDataWeightClicked)
        self._ui.groupFitDataWeight_lineEdit.editingFinished.connect(self._groupFitDataWeightEntered)
        self._ui.groupFitStrainPenalty_checkBox.clicked.connect(self._groupFitStrainPenaltyClicked)
        self._ui.groupFitStrainPenalty_lineEdit.editingFinished.connect(self._groupFitStrainPenaltyEntered)
        self._ui.groupFitCurvaturePenalty_checkBox.clicked.connect(self._groupFitCurvaturePenaltyClicked)
        self._ui.groupFitCurvaturePenalty_lineEdit.editingFinished.connect(self._groupFitCurvaturePenaltyEntered)

    def _updateGroupSettingWidgets(self):
        """
        Update and display group setting widgets for currentFitterStep
        """
        #isAlign = isinstance(self._currentFitterStep, FitterStepAlign)
        isConfig = isinstance(self._currentFitterStep, FitterStepConfig)
        isFit = isinstance(self._currentFitterStep, FitterStepFit)
        if isConfig:
            self._updateGroupConfigCentralProjection()
            self._updateGroupConfigDataProportion()
        elif isFit:
            self._updateGroupFitDataWeight()
            self._updateGroupFitStrainPenalty()
            self._updateGroupFitCurvaturePenalty()
        self._ui.groupConfigCentralProjection_checkBox.setVisible(isConfig)
        self._ui.groupConfigSetCentralProjection_checkBox.setVisible(isConfig)
        self._ui.groupConfigDataProportion_checkBox.setVisible(isConfig)
        self._ui.groupConfigDataProportion_lineEdit.setVisible(isConfig)
        self._ui.groupFitDataWeight_checkBox.setVisible(isFit)
        self._ui.groupFitDataWeight_lineEdit.setVisible(isFit)
        self._ui.groupFitStrainPenalty_checkBox.setVisible(isFit)
        self._ui.groupFitStrainPenalty_lineEdit.setVisible(isFit)
        self._ui.groupFitCurvaturePenalty_checkBox.setVisible(isFit)
        self._ui.groupFitCurvaturePenalty_lineEdit.setVisible(isFit)

    def _groupSettingsGroupChanged(self, index):
        """
        Callback for change in group settings field chooser widget.
        """
        groupName = self._getGroupSettingsGroupName()
        self._model.setSelectHighlightGroupByName(groupName)
        self._updateGroupSettingWidgets()

    def _getGroupSettingsGroupName(self):
        group = self._ui.groupSettings_fieldChooser.getField()
        groupName = None
        if group:
            groupName = group.getName()
        return groupName

    def _getGroupSettingDisplayState(self, func):
        groupName = self._getGroupSettingsGroupName()
        data, isLocallySet, inheritable = func(groupName)
        realFormat = "{:.4g}"
        lineEditDisable = True
        checkBoxTristate = False
        checkBoxState = QtCore.Qt.Unchecked
        if isinstance(data, float):
            data = realFormat.format(data)
        elif isinstance(data, list):
            data = ", ".join(realFormat.format(e) for e in data)
        else:
            assert isinstance(data, bool)
        if inheritable:
            checkBoxTristate = True
            if isLocallySet is not None:
                checkBoxState = QtCore.Qt.PartiallyChecked
        if isLocallySet:
            checkBoxState = QtCore.Qt.Checked
            lineEditDisable = False
        return checkBoxTristate,checkBoxState,lineEditDisable,data

    def _updateGroupConfigCentralProjection(self):
        checkBoxTristate,checkBoxState,lineEditDisable,isCentralProjection = self._getGroupSettingDisplayState(self._getConfig().getGroupCentralProjection)
        self._ui.groupConfigCentralProjection_checkBox.setTristate(checkBoxTristate)
        self._ui.groupConfigCentralProjection_checkBox.setCheckState(checkBoxState)        
        self._ui.groupConfigSetCentralProjection_checkBox.setDisabled(lineEditDisable)
        self._ui.groupConfigSetCentralProjection_checkBox.setCheckState(QtCore.Qt.Checked if isCentralProjection else QtCore.Qt.Unchecked)

    def _groupConfigCentralProjectionClicked(self):
        checkState = self._ui.groupConfigCentralProjection_checkBox.checkState()
        groupName = self._getGroupSettingsGroupName()
        if checkState == QtCore.Qt.Unchecked:
            self._getConfig().setGroupCentralProjection(groupName, None)
        elif checkState == QtCore.Qt.PartiallyChecked:
            self._getConfig().clearGroupCentralProjection(groupName)
        else:
            self._groupConfigSetCentralProjectionClicked()
        self._updateGroupConfigCentralProjection()

    def _groupConfigSetCentralProjectionClicked(self):
        state = self._ui.groupConfigSetCentralProjection_checkBox.checkState()
        config = self._getConfig()
        groupName = self._getGroupSettingsGroupName()
        if config.setGroupCentralProjection(groupName,state == QtCore.Qt.Checked):
            fitterSteps = self._fitter.getFitterSteps()
            index = fitterSteps.index(config)
            if config.hasRun() and (((index + 1) == len(fitterSteps)) or (not fitterSteps[index + 1].hasRun())):
                config.run()
                self._refreshStepItem(config)
                self._refreshGraphics()

    def _updateGroupConfigDataProportion(self):
        checkBoxTristate,checkBoxState,lineEditDisable,dataProportionStr = self._getGroupSettingDisplayState(self._getConfig().getGroupDataProportion)
        self._ui.groupConfigDataProportion_checkBox.setTristate(checkBoxTristate)
        self._ui.groupConfigDataProportion_checkBox.setCheckState(checkBoxState)        
        self._ui.groupConfigDataProportion_lineEdit.setDisabled(lineEditDisable)
        self._ui.groupConfigDataProportion_lineEdit.setText(dataProportionStr)

    def _groupConfigDataProportionClicked(self):
        checkState = self._ui.groupConfigDataProportion_checkBox.checkState()
        groupName = self._getGroupSettingsGroupName()
        if checkState == QtCore.Qt.Unchecked:
            self._getConfig().setGroupDataProportion(groupName, None)
        elif checkState == QtCore.Qt.PartiallyChecked:
            self._getConfig().clearGroupDataProportion(groupName)
        else:
            self._groupConfigDataProportionEntered()
        self._updateGroupConfigDataProportion()

    def _groupConfigDataProportionEntered(self):
        value = QLineEdit_parseRealNonNegative(self._ui.groupConfigDataProportion_lineEdit)
        groupName = self._getGroupSettingsGroupName()
        if value > 0.0:
            self._getConfig().setGroupDataProportion(groupName, value)
        else:
            print("Invalid model Data Proportion entered")
        self._updateGroupConfigDataProportion()

    def _updateGroupFitDataWeight(self):
        checkBoxTristate,checkBoxState,lineEditDisable,dataWeightStr = self._getGroupSettingDisplayState(self._getFit().getGroupDataWeight)
        self._ui.groupFitDataWeight_checkBox.setTristate(checkBoxTristate)
        self._ui.groupFitDataWeight_checkBox.setCheckState(checkBoxState)
        self._ui.groupFitDataWeight_lineEdit.setDisabled(lineEditDisable)
        self._ui.groupFitDataWeight_lineEdit.setText(dataWeightStr)

    def _groupFitDataWeightClicked(self):
        checkState = self._ui.groupFitDataWeight_checkBox.checkState()
        groupName = self._getGroupSettingsGroupName()
        if checkState == QtCore.Qt.Unchecked:
            self._getFit().setGroupDataWeight(groupName, None)
        elif checkState == QtCore.Qt.PartiallyChecked:
            self._getFit().clearGroupDataWeight(groupName)
        else:
            self._groupFitDataWeightEntered()
        self._updateGroupFitDataWeight()

    def _groupFitDataWeightEntered(self):
        value = QLineEdit_parseRealNonNegative(self._ui.groupFitDataWeight_lineEdit)
        groupName = self._getGroupSettingsGroupName()
        if value > 0.0:
            self._getFit().setGroupDataWeight(groupName, value)
        else:
            print("Invalid model Data Weight entered")
        self._updateGroupFitDataWeight()

    def _updateGroupFitStrainPenalty(self):
        checkBoxTristate,checkBoxState,lineEditDisable,dataStr = self._getGroupSettingDisplayState(self._getFit().getGroupStrainPenalty)
        self._ui.groupFitStrainPenalty_checkBox.setTristate(checkBoxTristate)
        self._ui.groupFitStrainPenalty_checkBox.setCheckState(checkBoxState)        
        self._ui.groupFitStrainPenalty_lineEdit.setDisabled(lineEditDisable)
        self._ui.groupFitStrainPenalty_lineEdit.setText(dataStr)

    def _groupFitStrainPenaltyClicked(self):
        checkState = self._ui.groupFitStrainPenalty_checkBox.checkState()
        groupName = self._getGroupSettingsGroupName()
        if checkState == QtCore.Qt.Unchecked:
            self._getFit().setGroupStrainPenalty(groupName, None)
        elif checkState == QtCore.Qt.PartiallyChecked:
            self._getFit().clearGroupStrainPenalty(groupName)
        else:
            self._groupFitStrainPenaltyEntered()
        self._updateGroupFitStrainPenalty()

    def _groupFitStrainPenaltyEntered(self):
        value = QLineEdit_parseVectors(self._ui.groupFitStrainPenalty_lineEdit)
        groupName = self._getGroupSettingsGroupName()
        self._getFit().setGroupStrainPenalty(groupName, value)
        self._updateGroupFitStrainPenalty()

    def _updateGroupFitCurvaturePenalty(self):
        checkBoxTristate,checkBoxState,lineEditDisable,dataStr = self._getGroupSettingDisplayState(self._getFit().getGroupCurvaturePenalty)
        self._ui.groupFitCurvaturePenalty_checkBox.setTristate(checkBoxTristate)
        self._ui.groupFitCurvaturePenalty_checkBox.setCheckState(checkBoxState)
        self._ui.groupFitCurvaturePenalty_lineEdit.setDisabled(lineEditDisable)
        self._ui.groupFitCurvaturePenalty_lineEdit.setText(dataStr)

    def _groupFitCurvaturePenaltyClicked(self):
        checkState = self._ui.groupFitCurvaturePenalty_checkBox.checkState()
        groupName = self._getGroupSettingsGroupName()
        if checkState == QtCore.Qt.Unchecked:
            self._getFit().setGroupCurvaturePenalty(groupName, None)
        elif checkState == QtCore.Qt.PartiallyChecked:
            self._getFit().clearGroupCurvaturePenalty(groupName)
        else:
            self._groupFitCurvaturePenaltyEntered()
        self._updateGroupFitCurvaturePenalty()

    def _groupFitCurvaturePenaltyEntered(self):
        value = QLineEdit_parseVectors(self._ui.groupFitCurvaturePenalty_lineEdit)
        groupName = self._getGroupSettingsGroupName()
        self._getFit().setGroupCurvaturePenalty(groupName, value)
        self._updateGroupFitCurvaturePenalty()

# === config widgets ===

    def _setupConfigWidgets(self):
        """
        Set up config widgets and display values from fitter object.
        """
        self._ui.configModelCoordinates_fieldChooser.setRegion(self._region)
        self._ui.configModelCoordinates_fieldChooser.setNullObjectName("-")
        self._ui.configModelCoordinates_fieldChooser.setConditional(field_is_managed_coordinates)
        self._ui.configModelCoordinates_fieldChooser.setField(self._fitter.getModelCoordinatesField())
        self._ui.configFibreOrientation_fieldChooser.setRegion(self._region)
        self._ui.configFibreOrientation_fieldChooser.setNullObjectName("-")
        self._ui.configFibreOrientation_fieldChooser.setConditional(field_is_managed_real_1_to_3_components)
        self._ui.configFibreOrientation_fieldChooser.setField(self._fitter.getFibreField())
        self._ui.configDataCoordinates_fieldChooser.setRegion(self._region)
        self._ui.configDataCoordinates_fieldChooser.setNullObjectName("-")
        self._ui.configDataCoordinates_fieldChooser.setConditional(field_is_managed_coordinates)
        self._ui.configDataCoordinates_fieldChooser.setField(self._fitter.getDataCoordinatesField())
        self._ui.configMarkerGroup_fieldChooser.setRegion(self._region)
        self._ui.configMarkerGroup_fieldChooser.setNullObjectName("-")
        self._ui.configMarkerGroup_fieldChooser.setConditional(field_is_managed_group)
        self._ui.configMarkerGroup_fieldChooser.setField(self._fitter.getMarkerGroup())
        self._ui.configDiagnosticLevel_spinBox.setValue(self._fitter.getDiagnosticLevel())

    def _makeConnectionsConfig(self):
        self._ui.configModelCoordinates_fieldChooser.currentIndexChanged.connect(self._configModelCoordinatesFieldChanged)
        self._ui.configFibreOrientation_fieldChooser.currentIndexChanged.connect(self._configFibreOrientationFieldChanged)
        self._ui.configDataCoordinates_fieldChooser.currentIndexChanged.connect(self._configDataCoordinatesFieldChanged)
        self._ui.configMarkerGroup_fieldChooser.currentIndexChanged.connect(self._configMarkerGroupChanged)
        self._ui.configDiagnosticLevel_spinBox.valueChanged.connect(self._configDiagnosticLevelValueChanged)

    def _getConfig(self):
        config = self._currentFitterStep
        assert isinstance(config, FitterStepConfig)
        return config

    def _updateConfigWidgets(self):
        """
        Update config widgets to display settings for Fitter.
        """
        self._updateGroupSettingWidgets()

    def _configModelCoordinatesFieldChanged(self, index):
        """
        Callback for change in model coordinates field chooser widget.
        """
        field = self._ui.configModelCoordinates_fieldChooser.getField()
        if field:
            self._fitter.setModelCoordinatesField(field)
            self._model.createGraphics()

    def _configFibreOrientationFieldChanged(self, index):
        """
        Callback for change in model coordinates field chooser widget.
        """
        self._fitter.setFibreField(self._ui.configFibreOrientation_fieldChooser.getField())

    def _configDataCoordinatesFieldChanged(self, index):
        """
        Callback for change in data coordinates field chooser widget.
        """
        field = self._ui.configDataCoordinates_fieldChooser.getField()
        if field:
            self._fitter.setDataCoordinatesField(field)
            self._model.createGraphics()

    def _configMarkerGroupChanged(self, index):
        """
        Callback for change in marker group field chooser widget.
        """
        group = self._ui.configMarkerGroup_fieldChooser.getField()
        if group:
            self._fitter.setMarkerGroup(group)
            self._model.createGraphics()

    def _configDiagnosticLevelValueChanged(self, value):
        self._fitter.setDiagnosticLevel(value)

# === align widgets ===

    def _makeConnectionsAlign(self):
        self._ui.alignGroups_checkBox.clicked.connect(self._alignGroupsClicked)
        self._ui.alignMarkers_checkBox.clicked.connect(self._alignMarkersClicked)
        self._ui.alignRotation_lineEdit.editingFinished.connect(self._alignRotationEntered)
        self._ui.alignScale_lineEdit.editingFinished.connect(self._alignScaleEntered)
        self._ui.alignTranslation_lineEdit.editingFinished.connect(self._alignTranslationEntered)

    def _getAlign(self):
        align = self._currentFitterStep
        assert isinstance(align, FitterStepAlign)
        return align

    def _updateAlignWidgets(self):
        """
        Update align widgets to display parameters from current align step.
        """
        align = self._getAlign()
        realFormat = "{:.4g}"
        self._ui.alignGroups_checkBox.setCheckState(QtCore.Qt.Checked if align.isAlignGroups() else QtCore.Qt.Unchecked)
        self._ui.alignMarkers_checkBox.setCheckState(QtCore.Qt.Checked if align.isAlignMarkers() else QtCore.Qt.Unchecked)
        self._ui.alignRotation_lineEdit.setText(", ".join(realFormat.format(value) for value in align.getRotation()))
        self._ui.alignScale_lineEdit.setText(realFormat.format(align.getScale()))
        self._ui.alignTranslation_lineEdit.setText(", ".join(realFormat.format(value) for value in align.getTranslation()))

    def _alignGroupsClicked(self):
        state = self._ui.alignGroups_checkBox.checkState()
        self._getAlign().setAlignGroups(state == QtCore.Qt.Checked)

    def _alignMarkersClicked(self):
        state = self._ui.alignMarkers_checkBox.checkState()
        self._getAlign().setAlignMarkers(state == QtCore.Qt.Checked)

    def _alignRotationEntered(self):
        values = QLineEdit_parseVector3(self._ui.alignRotation_lineEdit)
        if values:
            self._getAlign().setRotation(values)
        else:
            print("Invalid model rotation Euler angles entered")
        self._updateAlignWidgets()

    def _alignScaleEntered(self):
        value = QLineEdit_parseRealNonNegative(self._ui.alignScale_lineEdit)
        if value > 0.0:
            self._getAlign().setScale(value)
        else:
            print("Invalid model scale entered")
        self._updateAlignWidgets()

    def _alignTranslationEntered(self):
        values = QLineEdit_parseVector3(self._ui.alignTranslation_lineEdit)
        if values:
            self._getAlign().setTranslation(values)
        else:
            print("Invalid model translation entered")
        self._updateAlignWidgets()

# === fit widgets ===

    def _makeConnectionsFit(self):
        self._ui.fitIterations_spinBox.valueChanged.connect(self._fitIterationsValueChanged)
        self._ui.fitMaximumSubIterations_spinBox.valueChanged.connect(self._fitMaximumSubIterationsValueChanged)
        self._ui.fitUpdateReferenceState_checkBox.clicked.connect(self._fitUpdateReferenceStateClicked)

    def _getFit(self):
        assert isinstance(self._currentFitterStep, FitterStepFit)
        return self._currentFitterStep

    def _updateFitWidgets(self):
        """
        Update fit widgets to display parameters from fit step.
        """
        fit = self._getFit()
        realFormat = "{:.16}"
        self._ui.fitIterations_spinBox.setValue(fit.getNumberOfIterations())
        self._ui.fitMaximumSubIterations_spinBox.setValue(fit.getMaximumSubIterations())
        self._ui.fitUpdateReferenceState_checkBox.setCheckState(QtCore.Qt.Checked if fit.isUpdateReferenceState() else QtCore.Qt.Unchecked)
        self._updateGroupSettingWidgets()

    def _fitLineWeightEntered(self):
        value = QLineEdit_parseRealNonNegative(self._ui.fitLineWeight_lineEdit)
        if value >= 0.0:
            self._getFit().setLineWeight(value)
        else:
            print("Invalid line weight; must be non-negative")
        self._updateFitWidgets()

    def _fitMarkerWeightEntered(self):
        value = QLineEdit_parseRealNonNegative(self._ui.fitMarkerWeight_lineEdit)
        if value >= 0.0:
            self._getFit().setMarkerWeight(value)
        else:
            print("Invalid marker weight; must be non-negative")
        self._updateFitWidgets()

    def _fitStrainPenaltyEntered(self):
        value = QLineEdit_parseRealNonNegative(self._ui.fitStrainPenalty_lineEdit)
        if value >= 0.0:
            self._getFit().setStrainPenaltyWeight(value)
        else:
            print("Invalid penalty weight; must be non-negative")
        self._updateFitWidgets()

    def _fitCurvaturePenaltyEntered(self):
        value = QLineEdit_parseRealNonNegative(self._ui.fitCurvaturePenalty_lineEdit)
        if value >= 0.0:
            self._getFit().setCurvaturePenaltyWeight(value)
        else:
            print("Invalid penalty weight; must be non-negative")
        self._updateFitWidgets()

    def _fitEdgeDiscontinuityPenaltyEntered(self):
        value = QLineEdit_parseRealNonNegative(self._ui.fitEdgeDiscontinuityPenalty_lineEdit)
        if value >= 0.0:
            self._getFit().setEdgeDiscontinuityPenaltyWeight(value)
        else:
            print("Invalid penalty weight; must be non-negative")
        self._updateFitWidgets()

    def _fitIterationsValueChanged(self, value):
        self._getFit().setNumberOfIterations(value)

    def _fitMaximumSubIterationsValueChanged(self, value):
        self._getFit().setMaximumSubIterations(value)

    def _fitUpdateReferenceStateClicked(self):
        state = self._ui.fitUpdateReferenceState_checkBox.checkState()
        self._getFit().setUpdateReferenceState(state == QtCore.Qt.Checked)
