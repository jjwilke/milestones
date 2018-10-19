import matplotlib.pyplot as plt

def getMilestone(path):
  import os
  try:
    vendor, ms = os.path.split(path)
    ms = ms.rstrip(".py")
    module = vendor + "." + ms
    i  = __import__(module, fromlist=[])
    return i, vendor, ms
  except Exception as e:
    import sys
    sys.stderr.write("Failed importing  %s\n%s\n" % (module, e))
  return None, None, None

def getMilestones(vendor):
  import glob
  import os
  import pandas as pd
  import pprint
  pp = pprint.PrettyPrinter(indent=4)
  globber = os.path.join(vendor, "*.py")
  allfiles = glob.glob(globber)

  columns = [
    "name",
    "description", 
    "components",
    "deadline",
    "keywords"
  ]

  data = {}

  mods = []

  for f in allfiles:
    if "__init__" in f:
      continue

    mod, vendor, name = getMilestone(f) 
    if not mod: continue

    ms_mod = getattr(mod, name)
    columns.append(name)
    mods.append((ms_mod,name))

  for ms_mod, name in mods:
    my_cols = []
    for col in columns:
      try:
        attr = getattr(ms_mod, col) 
        my_cols.append(attr)
      except:
        my_cols.append("")

    data[name] = my_cols
  
  df = pd.DataFrame.from_dict(data, orient='index', columns=columns)
  return df

class Dependency:
  
  def __init__(self, src, dst, label):
    self.label = label

    self.x = src.x+1
    self.y = src.y
    self.dx = dst.x - (src.x+1)
    if src.x == dst.x:
      self.dx = 0
    self.dy = 0
    if src.y > dst.y:
      self.dy = src.y - dst.y - 1
      self.y = dst.y+1
    else:
      self.dy = dst.y - src.y - 1
      self.y = self.y+1

    self.center = (self.x + 0.5*self.dx, self.y+0.5*self.dy)

    self.arrow = plt.Arrow(self.x, self.y, self.dx, self.dy)

class Milestone:

  startYear = 2017

  colors = [
    "blue",
    "green",
    "red",
    "black",
    "orange",
  ]

  def __init__(self, name, number, due, description):
    if due:
      year, quarter = due.split()
      quarter = int(quarter.lower().strip("q"))
      year = int(year)
      self.due = (year-self.startYear)*4 + (quarter-1)
    else:
      self.due = 12 #far in future

    self.name = name

    self.number = number

    self.x = 2*self.due
    self.y = 2*self.number

    self.rect = plt.Rectangle((self.x,self.y), 1, 1, fc=self.colors[self.number])
    self.description = description

    self.lines = []

  def input_to(self, milestone, information):
    if self.x > milestone.x:
      sys.exit("Milestone %d inputs to Milestone %d, but comes after" % (self.number, milestone.number))

    self.lines.append(Dependency(self,milestone,information))

  def add_labeled_patch(self, ax, index, item, label, xy):
    patch = ax.add_patch(item)
    annotate = ax.annotate(label, xy=xy, xytext=(0,0),
                           color='w', ha='center', xycoords='data',
                           textcoords='offset points',
                           fontsize=8, bbox=dict(boxstyle='round, pad=.5',
                                                 fc=self.colors[self.number],
                                                 lw=1, zorder=1))
    ax.add_patch(patch)
    patch.set_gid('mypatch_{:03d}'.format(index))
    annotate.set_gid('mytooltip_{:03d}'.format(index))

  def add_labeled_patches(self, ax, index):
    self.add_labeled_patch(ax, index, self.rect, self.description, self.rect.get_xy())
    index += 1

    for dep in self.lines:
      self.add_labeled_patch(ax, index, dep.arrow, dep.label, dep.center)
      index += 1
    return index

  def add_as_tooltip(self, ax, xmlid, index, item, label):
    # Hide the tooltips
    tooltip = xmlid['mytooltip_{:03d}'.format(index)]
    tooltip.set('visibility', 'hidden')
    # Assign onmouseover and onmouseout callbacks to patches.
    mypatch = xmlid['mypatch_{:03d}'.format(index)]
    mypatch.set('onmouseover', "ShowTooltip(this)")
    mypatch.set('onmouseout', "HideTooltip(this)")

  def add_tooltips(self, ax, xmlid, index):
    self.add_as_tooltip(ax, xmlid, index, self.rect, self.description)
    index += 1

    for dep in self.lines:
      self.add_as_tooltip(ax, xmlid, index, dep.arrow, dep.label)
      index += 1
    return index


def plotMilestones(milestones, prefix):
  import xml.etree.ElementTree as ET
  from io import BytesIO

  fig, ax = plt.subplots()
  ET.register_namespace("", "http://www.w3.org/2000/svg")

  max_x = 0
  max_y = 0
  index = 0
  for m in milestones:
    index = m.add_labeled_patches(ax, index)
    max_x = max(max_x, m.x)
    max_y = max(max_y, m.y)

    # these are matplotlib.patch.Patch properties
    props = dict(boxstyle='round', facecolor=m.rect.get_facecolor(), alpha=0.63)

    # place a text box in upper left in axes coords
    header = ax.text(-2, m.y+0.2, m.name, color="white",
                     verticalalignment='bottom', bbox=props)

  ax.set_xlim(-2, max_x + 1)
  ax.set_ylim(0, max_y + 1)
  xticks = []
  xlabels = []
  for i in range(0, max_x+1, 2):
    xticks.append(i)
    xlabels.append("Q%d" % (i/2))
  ax.set_xticks(xticks)
  ax.set_xticklabels(xlabels)
  ax.set_aspect('equal')
  f = BytesIO()
  plt.savefig(f, format="svg")
  # Insert the script at the top of the file and save it.
  tree, xmlid = ET.XMLID(f.getvalue())
  tree.set('onload', 'init(evt)')
  # This is the script defining the ShowTooltip and HideTooltip functions.
  script = """
    <script type="text/ecmascript">
    <![CDATA[

    function init(evt) {
        if ( window.svgDocument == null ) {
            svgDocument = evt.target.ownerDocument;
            }
        }

    function ShowTooltip(obj) {
        var cur = obj.id.split("_")[1];
        var tip = svgDocument.getElementById('mytooltip_' + cur);
        tip.setAttribute('visibility',"visible")
        }

    function HideTooltip(obj) {
        var cur = obj.id.split("_")[1];
        var tip = svgDocument.getElementById('mytooltip_' + cur);
        tip.setAttribute('visibility',"hidden")
        }

    ]]>
    </script>
    """


  index = 0
  for m in milestones:
    index = m.add_tooltips(ax, xmlid, index)

  tree.insert(0, ET.XML(script))
  name = "%s.svg" % prefix
  ET.ElementTree(tree).write(name)
  return name
  

def getGantt(prefix, df):
  ms_map = {}
  ms_list = []
  number = 0
  for index, row in df.iterrows():
    m = Milestone(index, number, row["deadline"], row["description"])
    ms_map[index] = m
    ms_list.append(m)
    number += 1

  for src_index, src_row in df.iterrows():
    my_ms = ms_map[src_index]
    for dst_index, dst_row in df.iterrows():
      support = src_row[dst_index]
      if support:
        my_ms.input_to(ms_map[dst_index], support)

  return plotMilestones(ms_list, prefix)
      
  


    

    

  




    
