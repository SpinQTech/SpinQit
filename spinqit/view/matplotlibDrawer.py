# Copyright 2021 SpinQ Technology Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
from ..compiler.ir import IntermediateRepresentation, NodeType
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import re
from .utils import dag_to_layers, format_params, parse_comparator

# these are the base value in a graph with no scale, which means figure width = (xmax-xmin)/100 inches with dpi = 100
GRAPH_MARGIN_X = 24
GRAPH_MARGIN_Y = 40
GATE_WIDTH = 72 # standard single-bit gate width
GATE_MIN_PADDING = 4 # minimum padding from text to margin
GATE_X_GAP = 36
GATE_TITLE_FONT_SIZE = 13
BIT_TAG_FONT_SIZE = 10
GATE_TIPS_FONT_SIZE = 8
LINE_GAP = 96
GATE_Y_GAP = LINE_GAP - GATE_WIDTH
LINE_WIDTH = 1
SCATTER_RADIUS= 2
BIT_TAG_WIDTH = 30
BIT_TAG_GAP = 7
CORE_RADIUS= 6
EDGE_ROUND_SIZE=0
TAG_MARGIN = 6 # local parameter tag, measure tag, condition tag
# other styles
BIT_TYPE_QUBIT = 'qubit'
BIT_TYPE_CLBIT = 'clbit'
QUBIT_LINE_COLOR = '#C1C9D4'
CLBIT_LINE_COLOR = '#7D83A0'
QUBIT_TAG_COLOR = '#073862'
CLBIT_TAG_COLOR = '#787D9B'
GATE_TXT_COLOR = '#FFFFFF'
CTRL_LINE_COLOR = '#073862'
# special gate style width
BARRIER_WIDTH = 2
SWAP_WIDTH = 26
SWAP_LINE_WIDTH = 2.6
GATE_WITH_LOCAL_QUBITS_PADDING = 24 # padding for custom gate with more than 1 qubits to mark its local qubits on the left
CLBITS_COLLAPSE_LINE_GAP = 9
COND_LINE_COLOR = '#7E91FF'
MEASURE_COLOR = '#FF7E88' # both measure line color and measure gate color
MEASURE_EDGE_COLOR = '#AD557C' # measure gate edge color

# zorders, larger will on the top
BACKGROUND_ZORDER = 1
CONNECTION_ZORDER = 2
GATE_SHAPE_ZORDER = 3
GATE_TXT_ZORDER = 4

class MatplotlibDrawer:
    """Matplotlib drawer class called from circuit_drawer"""
    def __init__(self, ir: IntermediateRepresentation, clbit_extend = False, decompose_level=0):
        if decompose_level > 1 or decompose_level < 0:
            raise ValueError("Decompose level can only be 0 or 1.")
        self._ir = ir
        self._clbit_extend = clbit_extend
        self._qubit_tag = 'Q'
        self._clbit_tag = 'C'
        self._figure = plt.figure()
        self._ax = self._figure.add_subplot(111, aspect='equal')
        self._ax.axis("off")
        self._decompose_level = decompose_level # level to decompose the customized gate
        self._qubit_size = 0
        self._clbit_size = 0
        self._max_slot = 0
        self._sorted_vs_list = []
        self._layers = []
        self._layers_width = []

    """
    Map ir to layers functions
    """

    # calculate the width of each layers
    def _calc_layers_width(self):
        self._layers_width.clear()

        tmp_ax = self._figure.add_subplot(111, aspect='equal')
        tmp_render = self._figure.canvas.get_renderer()
        xmin, xmax, ymin, ymax = -5, 200, 0, 100
        tmp_ax.set_xlim(xmin, xmax)
        tmp_ax.set_ylim(ymin, ymax)
        self._figure.set_size_inches((xmax-xmin)/100, (ymax-ymin)/100)

        for idx in range(len(self._layers)):
            lw = 0
            for node in self._layers[idx]:
                gate_width = GATE_WIDTH
                if node['name'] not in ['SWAP', 'MEASURE', 'BARRIER']: # exclude special gates
                    gate_padding = GATE_MIN_PADDING
                    if node['type'] == NodeType.caller.value and len(node['qubits']) > 1:
                        gate_padding = GATE_WITH_LOCAL_QUBITS_PADDING
                    title = tmp_ax.text(0, 0, node['name'], fontsize=GATE_TITLE_FONT_SIZE, zorder=2)
                    title_bb = title.get_window_extent(renderer=tmp_render).transformed(plt.gca().transData.inverted())
                    gate_width = title_bb.width + gate_padding*2
                    if 'params' in node and node['params'] is not None and len(node['params']) > 0:
                        # round to 3 digits after 0
                        paramStr = '(' + ', '.join([format_params(i) for i in node['params']]) + ')' 
                        params = tmp_ax.text(0, 0, paramStr, fontsize=GATE_TIPS_FONT_SIZE, zorder=2)
                        params_bb = params.get_window_extent(renderer=tmp_render).transformed(plt.gca().transData.inverted())
                        gate_width = max(gate_width, params_bb.width + gate_padding*2)
                    gate_width = max(gate_width, GATE_WIDTH)
                node["width"] = gate_width
                lw = max(lw, gate_width)
            self._layers_width.append(lw)
        
        tmp_ax.remove()

    """
    Draw functions
    """

    # draw the circuit
    # @params: [filename] - save image filename
    def draw(self, filename = None):
        # convert ir to layers
        self._qubit_size, self._clbit_size, self._max_slot, self._layers = dag_to_layers(self._ir, self._decompose_level)
        self._calc_layers_width()

        xmin, xmax, ymin = - BIT_TAG_WIDTH - BIT_TAG_GAP - GRAPH_MARGIN_X, sum(self._layers_width) + GATE_X_GAP*(self._max_slot+1) + GRAPH_MARGIN_X, 0
        clbits_height = 0
        gap_qubits_clbits = GATE_WIDTH/2
        if self._clbit_size > 0:
            if self._clbit_extend:
                clbits_height = (self._clbit_size-1)*LINE_GAP
                gap_qubits_clbits = LINE_GAP
            else:
                clbits_height = CLBITS_COLLAPSE_LINE_GAP # 2 for the lower line of double line
                gap_qubits_clbits = LINE_GAP
        
        ymax = GRAPH_MARGIN_Y + GATE_WIDTH/2 + (self._qubit_size-1)*LINE_GAP + gap_qubits_clbits + clbits_height + GRAPH_MARGIN_Y
        self._ax.set_xlim(xmin, xmax)
        self._ax.set_ylim(ymax, ymin) # revert to change the direction of axis (increase from top to bottom)
        self._figure.set_size_inches((xmax-xmin)/100, (ymax-ymin)/100)

        self._draw_axis(self._qubit_size, self._clbit_size, self._max_slot)
        for idx in range(len(self._layers)):
            for node in self._layers[idx]:
                params = node['params'] if 'params' in node else None
                if node["name"] in ["CX", "CY", "CZ", "CP", "CCX"]:
                    self._draw_ctrl_gate(node['name'], node['qubits'], idx, node['type'], node['width'], params=params)
                elif node["name"] == "SWAP":
                    self._draw_swap_gate(node['name'], node['qubits'], idx)
                elif node["name"] == "MEASURE":
                    self._draw_measure(node['qubits'], node['in_clbits'], idx, params=params)
                elif node["name"] == "BARRIER":
                    self._draw_barrier(node['name'], node['qubits'], idx)
                else:
                    self._draw_simple_gate(node['name'], node['qubits'], idx, node['type'], node['width'], params=params)
                if 'in_conbits' in node and len(node["in_conbits"]) > 0:
                    self._draw_cond_line(node['name'], node['qubits'], node['in_conbits'], idx, node['cmp'], node['constant'])
        if filename is not None and len(filename) > 0:
            self._figure.savefig(filename, dpi='figure', bbox_inches="tight")


    # draw the axis of the circuit, including qubit tags, qubit lines, and the circle center of each (timeSlot, qubit) tuple
    # @params: [qnum] - total qubits number
    # @params: [slotNum] - total time slot number
    def _draw_axis(self, qnum: int, cnum:int, slotNum: int):

        q_scatter_x_list = []
        q_scatter_y_list = []

        for i in range(qnum):
            # y = (i+1)*LINE_GAP
            y_pos = self.cal_bit_y(i, BIT_TYPE_QUBIT)
            for j in range(slotNum):
                x_pos = self.cal_bit_x(j)
                q_scatter_x_list.append(x_pos)
                q_scatter_y_list.append(y_pos)
            self._ax.text(
                -BIT_TAG_GAP, y_pos,
                self._qubit_tag+'['+str(i)+']',
                ha="right", va="center",
                fontsize=BIT_TAG_FONT_SIZE,
                color=QUBIT_TAG_COLOR,
                zorder=BACKGROUND_ZORDER
            )
        
        line_width = sum(self._layers_width) + GATE_X_GAP*(slotNum+1)

        self._ax.hlines(q_scatter_y_list, 0, line_width, colors=[QUBIT_LINE_COLOR], linewidth=LINE_WIDTH, linestyle="solid",zorder=BACKGROUND_ZORDER)

        if cnum > 0:
            c_scatter_x_list = []
            c_scatter_y_list = []
            if self._clbit_extend:
                for i in range(cnum):
                    y_pos = self.cal_bit_y(i, BIT_TYPE_CLBIT)
                    for j in range(slotNum):
                        x_pos = self.cal_bit_x(j)
                        c_scatter_x_list.append(x_pos)
                        c_scatter_y_list.append(y_pos)
                    self._ax.text(
                        -BIT_TAG_GAP, y_pos,
                        self._clbit_tag+'['+str(i)+']',
                        ha="right", va="center",
                        fontsize=BIT_TAG_FONT_SIZE,
                        color=CLBIT_TAG_COLOR,
                        zorder=BACKGROUND_ZORDER
                    )
            else:
                height_after_qubits =  GRAPH_MARGIN_Y + GATE_WIDTH/2 + (self._qubit_size-1)*LINE_GAP
                first_line_height = height_after_qubits + LINE_GAP
                self._ax.plot([0, line_width], [first_line_height, first_line_height], color=CLBIT_LINE_COLOR, linewidth=LINE_WIDTH, linestyle="solid",zorder=BACKGROUND_ZORDER)
                circ = patches.Circle((1, first_line_height+CLBITS_COLLAPSE_LINE_GAP/2), 1, color=CLBIT_LINE_COLOR, linewidth=None, zorder=BACKGROUND_ZORDER)
                self._ax.add_patch(circ)
                self._ax.plot([0, line_width], [first_line_height+CLBITS_COLLAPSE_LINE_GAP, first_line_height+CLBITS_COLLAPSE_LINE_GAP], color=CLBIT_LINE_COLOR, linewidth=LINE_WIDTH, linestyle="solid",zorder=BACKGROUND_ZORDER)
                self._ax.text(
                    -BIT_TAG_GAP, first_line_height+CLBITS_COLLAPSE_LINE_GAP+3,
                    self._clbit_tag+str(self._clbit_size),
                    ha="right", va="bottom",
                    fontsize=BIT_TAG_FONT_SIZE,
                    color=CLBIT_TAG_COLOR,
                    zorder=BACKGROUND_ZORDER
                )
            self._ax.hlines(c_scatter_y_list, 0, line_width, colors=[CLBIT_LINE_COLOR], linewidth=LINE_WIDTH, linestyle="solid",zorder=BACKGROUND_ZORDER)

    # draw general gate that may cross multiple qubits
    # @params: [name] - gate name
    # @params: [qubits] - gate qubits
    # @params: [layer_idx] - layer_idx, current equal to time slot (start from 0)
    # @params: [gateType] - gate ir node type
    # @params: [width] - gate width, different from time slot width because there may be thinner or fatter gate in this time slot
    # @params: [params] - gate rotation params
    def _draw_simple_gate(self, name, qubits, layer_idx, gateType, width, **kargs):
        min_xy_pos = self.cal_core_pos((layer_idx, min(qubits)), BIT_TYPE_QUBIT) 
        # because current gate are all one time slot, min_xy_pos[0] is x_center

        gate_height = (max(qubits) - min(qubits) + 1)*(GATE_WIDTH + GATE_Y_GAP) - GATE_Y_GAP
        y_center = min_xy_pos[1] -GATE_WIDTH/2 + gate_height/2
        
        rect = patches.FancyBboxPatch((min_xy_pos[0]-width/2, min_xy_pos[1]-GATE_WIDTH/2), width, gate_height, color=self._color_picker(name), boxstyle=patches.BoxStyle("Round", pad=0, rounding_size=EDGE_ROUND_SIZE), zorder=GATE_SHAPE_ZORDER)
        self._ax.add_patch(rect)

        hasParams = 'params' in kargs and kargs['params'] is not None and len(kargs['params']) > 0
        # draw title
        title_y_pos = y_center - 10 if hasParams else y_center + 2
        self._ax.text(
            min_xy_pos[0],
            title_y_pos,
            name,
            ha="center",
            va="center",
            fontsize=GATE_TITLE_FONT_SIZE,
            color=GATE_TXT_COLOR,
            clip_on=True,
            zorder=GATE_TXT_ZORDER
        )
        # draw params
        if hasParams:
            # round to 3 digits after 0
            paramStr = '(' + ', '.join([format_params(i) for i in kargs["params"]]) + ')' 
            self._ax.text(
                min_xy_pos[0],
                y_center + 14,
                paramStr,
                ha="center",
                va="center",
                fontsize=GATE_TIPS_FONT_SIZE,
                color=GATE_TXT_COLOR,
                clip_on=True,
                zorder=GATE_TXT_ZORDER
            )
        # draw local params label
        if gateType == NodeType.caller.value and len(qubits) > 1:
            for idx, global_bit in enumerate(qubits):
                self._ax.text(
                    min_xy_pos[0]-width/2+TAG_MARGIN,
                    self.cal_bit_y(global_bit, BIT_TYPE_QUBIT),
                    str(idx),
                    ha="left",
                    va="center",
                    fontsize=GATE_TIPS_FONT_SIZE,
                    color=GATE_TXT_COLOR,
                    clip_on=True,
                    zorder=GATE_TXT_ZORDER
                )

    # draw general control gate
    # @params: [name] - gate name
    # @params: [qubits] - gate qubits (include controller and target, will be split inside this function)
    # @params: [layer_idx] - layer_idx, current equal to time slot (start from 0)
    # @params: [gateType] - gate ir node type
    # @params: [width] - gate width, different from time slot width because there may be thinner or fatter gate in this time slot
    # @params: [params] - gate rotation params
    def _draw_ctrl_gate(self, name, qubits, layer_idx, gateType, width, **kargs):
        if name == 'CCX':
            # the first two bits are controller bits, and others are target
            control_bits = qubits[:2]
            target_bits = qubits[2:]
        else:
            # the first one bit is controller bit, and others are target
            control_bits = qubits[:1]
            target_bits = qubits[1:]
        # draw control circles
        for cb in control_bits:
            xy_pos = self.cal_core_pos((layer_idx, cb), BIT_TYPE_QUBIT)
            circ = patches.Circle(xy_pos, CORE_RADIUS, color=CTRL_LINE_COLOR, linewidth=None, zorder=GATE_SHAPE_ZORDER)
            self._ax.add_patch(circ)
        # draw connection line
        min_qy = self.cal_bit_y(min(qubits), BIT_TYPE_QUBIT)
        max_qy = self.cal_bit_y(max(qubits), BIT_TYPE_QUBIT)
        qx_center = (layer_idx+1)*GATE_X_GAP + self._layers_width[layer_idx]/2 + sum(self._layers_width[:layer_idx])
        self._ax.plot([qx_center, qx_center], [min_qy, max_qy], color=CTRL_LINE_COLOR, linewidth=LINE_WIDTH, linestyle="solid",zorder=CONNECTION_ZORDER)
        # draw target gate
        self._draw_simple_gate(name, target_bits, layer_idx, gateType, width, **kargs)

    # draw condition line that read value back from classic bits for a quantum operation
    # @params: [name] - gate name
    # @params: [qubits] - quantum operation qubits
    # @params: [conbits] - classic bits read back value from
    # @params: [layer_idx] - layer_idx, current equal to time slot (start from 0)
    # @params: [comp] - condition comparator
    # @params: [constant] - condition compared value
    def _draw_cond_line(self, name, qubits, conbits, layer_idx, comp, constant):
        if comp is None or constant is None:
            raise ValueError('Condition judgement lacks variable.')
        tag = parse_comparator(comp) + ' ' + str(constant)
        max_qxy = self.cal_core_pos((layer_idx, max(qubits)), BIT_TYPE_QUBIT)
        if self._clbit_extend:
            max_cy = self.cal_bit_y(max(conbits), BIT_TYPE_CLBIT)
            for c in conbits:
                cy = self.cal_bit_y(c, BIT_TYPE_CLBIT)
                max_cy = max(max_cy, cy)
                circ = patches.Circle((max_qxy[0], cy), CORE_RADIUS, color=COND_LINE_COLOR, linewidth=None, zorder=GATE_SHAPE_ZORDER)
                self._ax.add_patch(circ)
            qy = max_qxy[1] if name == 'SWAP' else max_qxy[1]+GATE_WIDTH/2
            self._ax.plot([max_qxy[0], max_qxy[0]], [qy, max_cy], color=COND_LINE_COLOR, linewidth=LINE_WIDTH, linestyle="solid",zorder=CONNECTION_ZORDER)
        else:
            cy = self.cal_bit_y(0, BIT_TYPE_CLBIT)
            circ = patches.Circle((max_qxy[0], cy+CLBITS_COLLAPSE_LINE_GAP/2), CORE_RADIUS, color=COND_LINE_COLOR, linewidth=None, zorder=GATE_SHAPE_ZORDER)
            self._ax.add_patch(circ)
            qy = max_qxy[1] if name == 'SWAP' else max_qxy[1]+GATE_WIDTH/2
            self._ax.plot([max_qxy[0], max_qxy[0]], [qy, cy], color=COND_LINE_COLOR, linewidth=LINE_WIDTH, linestyle="solid",zorder=CONNECTION_ZORDER)
            self._ax.text(
                max_qxy[0],
                cy + CLBITS_COLLAPSE_LINE_GAP + TAG_MARGIN,
                tag,
                ha="center",
                va="top",
                fontsize=GATE_TIPS_FONT_SIZE,
                color=CLBIT_TAG_COLOR,
                zorder=GATE_TXT_ZORDER
            )

    # draw measure gate and its line point to classic bits
    # @params: [qubits] - gate qubits
    # @params: [clbits] - gate classic bits
    # @params: [layer_idx] - layer_idx, current equal to time slot (start from 0)
    def _draw_measure(self, qubits, clbits, layer_idx, **kargs):
        min_xy_pos = self.cal_core_pos((layer_idx, min(qubits)), BIT_TYPE_QUBIT) 
        # because current gate are all one time slot, min_xy_pos[0] is x_center

        gate_height = (max(qubits) - min(qubits) + 1)*(GATE_WIDTH + GATE_Y_GAP) - GATE_Y_GAP

        rect = patches.FancyBboxPatch((min_xy_pos[0]-GATE_WIDTH/2, min_xy_pos[1]-GATE_WIDTH/2), GATE_WIDTH, gate_height, fc=MEASURE_COLOR, ec=MEASURE_EDGE_COLOR, lw=4, boxstyle=patches.BoxStyle("Round", pad=0, rounding_size=EDGE_ROUND_SIZE), zorder=GATE_SHAPE_ZORDER)
        self._ax.add_patch(rect)
        rect.set_clip_path(rect)
        
        # draw icon
        # position of a measure icon in 72*72 svg
        measure_icon = "M47.4,29.3l9.8-10.1c0.7-0.7,0.7-1.9,0-2.6c-0.7-0.7-1.9-0.7-2.6,0L43.7,27.7c-2.4-0.8-5.1-1.3-7.8-1.3c-13.5,0-24.5,11-24.5,24.5c0,1,0.8,1.9,1.9,1.9q1.9-0.8,1.9-1.9c0-11.5,9.3-20.8,20.8-20.8c1.7,0,3.3,0.2,4.8,0.6L29.4,42.5c-0.7,0.7-0.7,1.9,0,2.6c0.4,0.4,0.8,0.5,1.3,0.5c0.5,0,1-0.2,1.3-0.6l12.6-13c7.1,3.3,12.1,10.5,12.1,18.9c0,1,0.8,1.9,1.9,1.9c1,0,1.9-0.8,1.9-1.9C60.5,41.6,55.2,33.4,47.4,29.3z"
        # SVG to Matplotlib
        codes, verts = self._svg_parse(measure_icon)
        # find global position
        icon_left_buttom = (min_xy_pos[0]-GATE_WIDTH/2, min_xy_pos[1]-GATE_WIDTH/2+gate_height/2-72/2)
        verts = np.array(icon_left_buttom) + verts
        path = Path(verts, codes)
        icon = patches.PathPatch(path, color=GATE_TXT_COLOR, zorder=GATE_TXT_ZORDER)
        self._ax.add_patch(icon)

        # draw connection to clbits
        max_qy = min_xy_pos[1]-GATE_WIDTH/2 + gate_height
        cy = self.cal_bit_y(clbits[0], BIT_TYPE_CLBIT)
        conn = patches.ConnectionPatch(xyA=(min_xy_pos[0], max_qy), xyB=(min_xy_pos[0], cy + CLBITS_COLLAPSE_LINE_GAP if not self._clbit_extend else cy), coordsA="data", arrowstyle="-|>", color=MEASURE_COLOR, linewidth=LINE_WIDTH, linestyle="solid",zorder=CONNECTION_ZORDER)
        self._ax.add_patch(conn)

        # mark clbit label if collapse
        tag = ''
        if len(clbits) > 5:
            clbits.sort()
            tag = str(clbits[0]) + '...' + str(clbits[-1])
        else:
            tag = str(', '.join([str(i) for i in clbits]))
        if not self._clbit_extend:
            self._ax.text(
                min_xy_pos[0] + TAG_MARGIN,
                cy - TAG_MARGIN - 4,
                tag,
                ha="left",
                va="center",
                fontsize=GATE_TIPS_FONT_SIZE,
                color=QUBIT_TAG_COLOR,
                zorder=GATE_TXT_ZORDER
            )

    # draw swap gate
    # @params: [name] - gate name
    # @params: [qubits] - gate qubits
    # @params: [layer_idx] - layer_idx, current equal to time slot (start from 0)
    def _draw_swap_gate(self, name, qubits, layer_idx, **kargs):
        min_xy_pos = self.cal_core_pos((layer_idx, min(qubits)), BIT_TYPE_QUBIT) 
        max_y_pos = self.cal_bit_y(max(qubits), BIT_TYPE_QUBIT)
        # because current gate are all one time slot, min_xy_pos[0] is x_center

        # draw cross
        self._ax.plot([min_xy_pos[0]-SWAP_WIDTH/2, min_xy_pos[0]+SWAP_WIDTH/2], [min_xy_pos[1]-SWAP_WIDTH/2, min_xy_pos[1]+SWAP_WIDTH/2], color=self._color_picker(name), linewidth=SWAP_LINE_WIDTH, linestyle="solid",zorder=GATE_SHAPE_ZORDER)
        self._ax.plot([min_xy_pos[0]+SWAP_WIDTH/2, min_xy_pos[0]-SWAP_WIDTH/2], [min_xy_pos[1]-SWAP_WIDTH/2, min_xy_pos[1]+SWAP_WIDTH/2], color=self._color_picker(name), linewidth=SWAP_LINE_WIDTH, linestyle="solid",zorder=GATE_SHAPE_ZORDER)
        self._ax.plot([min_xy_pos[0]-SWAP_WIDTH/2, min_xy_pos[0]+SWAP_WIDTH/2], [max_y_pos-SWAP_WIDTH/2, max_y_pos+SWAP_WIDTH/2], color=self._color_picker(name), linewidth=SWAP_LINE_WIDTH, linestyle="solid",zorder=GATE_SHAPE_ZORDER)
        self._ax.plot([min_xy_pos[0]+SWAP_WIDTH/2, min_xy_pos[0]-SWAP_WIDTH/2], [max_y_pos-SWAP_WIDTH/2, max_y_pos+SWAP_WIDTH/2], color=self._color_picker(name), linewidth=SWAP_LINE_WIDTH, linestyle="solid",zorder=GATE_SHAPE_ZORDER)
        # draw connection line
        self._ax.plot([min_xy_pos[0], min_xy_pos[0]], [min_xy_pos[1], max_y_pos], color=self._color_picker(name), linewidth=SWAP_LINE_WIDTH, linestyle="solid",zorder=CONNECTION_ZORDER)

    # draw barrier gate
    # @params: [name] - gate name
    # @params: [qubits] - gate qubits
    # @params: [layer_idx] - layer_idx, current equal to time slot (start from 0)
    def _draw_barrier(self, name, qubits, layer_idx):
        x_center = self.cal_bit_x(layer_idx)
        for q in qubits:
            y_center = self.cal_bit_y(q, BIT_TYPE_QUBIT)
            self._ax.plot([x_center, x_center], [y_center-GATE_WIDTH/2+1, y_center-1], color=self._color_picker(name), linewidth=BARRIER_WIDTH, linestyle="solid",zorder=GATE_SHAPE_ZORDER)
            self._ax.plot([x_center, x_center], [y_center+1, y_center+GATE_WIDTH/2-1], color=self._color_picker(name), linewidth=BARRIER_WIDTH, linestyle="solid",zorder=GATE_SHAPE_ZORDER)

    """
    Help functions
    """

    # calculate the x coordinate by a timeSlot (start 0), and a list of width of each time slot
    # @params: [x_idx] - timeslot index
    # @return: center x coordinate
    def cal_bit_x(self, x_idx):
        return (x_idx+1)*GATE_X_GAP + self._layers_width[x_idx]/2 + sum(self._layers_width[:x_idx])

    # calculate the y coordinate by a qubit idx (start 0)
    # @params: [y_idx] - bit index
    # @params: [bit_type] - is this a quantum bits or classic bits
    # @return: center y coordinate
    def cal_bit_y(self, y_idx, bit_type: str):
        if bit_type == BIT_TYPE_QUBIT:
            return GRAPH_MARGIN_Y + GATE_WIDTH/2 + (y_idx)*LINE_GAP # first line margin = margin + half gate width
        else:
            last_qubit_height = GRAPH_MARGIN_Y + GATE_WIDTH/2 + (self._qubit_size-1)*LINE_GAP
            if self._clbit_extend:
                return last_qubit_height + (y_idx+1)*LINE_GAP
            else:
                return last_qubit_height + LINE_GAP

    # calculate the x and y coordinate by (timeSlot, bit_idx) tuple and bit type
    # if this is a classic bit, should first add the height of all qubits
    # equivalent to the center of a single-bit gate at this time slot
    # @params: [xy_idx] - (timeSlot, bit_idx)
    # @params: [bit_type] - is this a quantum bits or classic bits
    # @return: center coordinate in (x,y) format
    def cal_core_pos(self, xy_idx: tuple, bit_type: str):
        return (self.cal_bit_x(xy_idx[0]), self.cal_bit_y(xy_idx[1], bit_type))


    # refer to tutorial https://matplotlib.org/stable/gallery/showcase/firefox.html
    # draw icon by svg path
    # @params: [path] - svg path
    def _svg_parse(self, path:str):
        commands = {'M': (Path.MOVETO,),
                    'L': (Path.LINETO,),
                    'Q': (Path.CURVE3,)*2,
                    'C': (Path.CURVE4,)*3,
                    'Z': (Path.CLOSEPOLY,)}
        verts = []
        codes = []
        cmd_values = re.split("([A-Za-z])", path)[1:]  # Split over commands.
        for cmd, values in zip(cmd_values[::2], cmd_values[1::2]):
            # Numbers are separated either by commas, or by +/- signs (but not at
            # the beginning of the string).
            points = ([*map(float, re.split(",|(?<!^)(?=[+-])", values))] if values
                    else [(0., 0.)])  # Only for "z/Z" (CLOSEPOLY).
            points = np.reshape(points, (-1, 2))
            if cmd.islower():
                points += verts[-1][-1]
            codes.extend(commands[cmd.upper()])
            verts.append(points)
        return np.array(codes), np.concatenate(verts)

    # gate color picker by gate name
    # @params: [gate_name] - gate name
    # @return: gate icon color
    def _color_picker(self, gate_name: str):
        if gate_name in ['H', 'I']:
            return '#4E77FF'
        elif gate_name in ['X', 'Y', 'Z', 'Rx', 'Ry', 'Rz', 'U']:
            return '#00B5ED' # Pauli gates
        elif gate_name in ['Rx', 'Ry', 'Rz', 'U']:
            return '#CC508A' # rotation gates
        elif gate_name in ['P', 'T', 'Td', 'S', 'Sd']:
            return '#533CFF' # Phase gates
        elif gate_name in ['CX', 'CNOT', 'CY', 'YCON', 'CZ', 'ZCON', 'CCX', 'CP']:
            return '#406C95' # Control gates
        elif gate_name == 'BARRIER':
            return '#E93039' # Barrier
        elif gate_name == 'MEASURE':
            return MEASURE_COLOR # Measure
        elif gate_name == 'SWAP':
            return '#5E55A2' # Swap
        else:
            return '#397C53'

# draw a png image for a circuit ir
# @params: [ir] - circuit ir
# @params: [filename] - save image filename
# @params: [clbit_extend] - show each classic bit in a row, or collapse all classic bits into one row
# @params: [decompose_level] - for decompose_level = n > 0, decomposed customized gates in the circuit recursively for n times
def draw(ir: IntermediateRepresentation, filename=None, clbit_extend = False, decompose_level=0):
    drawer = MatplotlibDrawer(ir, clbit_extend, decompose_level)
    drawer.draw(filename)
