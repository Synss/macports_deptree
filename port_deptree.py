#!/usr/bin/env python
# Copyright (c) 2014, 2015 Mathias Laurin
# BSD 3-Clause License (http://opensource.org/licenses/BSD-3-Clause)

r"""Print all dependencies required to build a port as a graph.

Usage:
    port_deptree.py PORTNAME [VARIANTS ...]

Example:
    port_deptree.py irssi -perl | dot -Tpdf -oirssi.pdf
    port_deptree.py $(port echo requested and outdated)\
            | dot -Tpdf | open -fa Preview

"""
from __future__ import print_function
import sys
_stdout, sys.stdout = sys.stdout, sys.stderr
import subprocess
import threading
import six
from six.moves.queue import Queue
from altgraph import Dot, Graph, GraphError
__version__ = "0.8"


def _(bytes):
    return bytes.decode("utf-8")


class ThreadHandler(threading.Thread):

    def __init__(self, func, queue):
        super(ThreadHandler, self).__init__()
        self.setDaemon(True)
        self.func = func
        self.queue = queue

    def run(self):
        while True:
            item = self.queue.get()
            self.func(item)
            self.queue.task_done()


class Fillcolor(object):

    Not_Installed = "moccasin"
    Outdated = "lightblue"
    Default = "white"


class Color(object):

    Not_Installed = "red"
    Outdated = "forestgreen"
    Default = "black"


def is_installed(portname):
    """Return True if `portname` is installed, False otherwise."""
    process = ["port", "installed", portname]
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        return not _(line).startswith("None")


def is_outdated(portname):
    """Return True if `portname` is outdated, False otherwise."""
    process = ["port", "outdated", portname]
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        return not _(line).startswith("No")


def get_deps(portname, variants):
    """Return `section, depname` dependents of `portname` with `variants`."""
    process = ["port", "deps", portname]
    process.extend(variants)
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        section, sep, children = _(line).partition(":")
        if not section.endswith("Dependencies"): continue
        for child in [child.strip() for child in children.split(",")]:
            yield section.split()[0].lower(), child


def decorate_node(node):
    """Color `node` if it is Outdated or not installed."""
    portname, style = node
    if not is_installed(portname):
        style["fillcolor"] = Fillcolor.Not_Installed
        style["color"] = Color.Not_Installed
    elif is_outdated(portname):
        style["fillcolor"] = Fillcolor.Outdated
        style["color"] = Color.Outdated


def make_graph(portname, variants, graph):
    """Traverse dependency tree of `portname` with `variants`.

    Args:
        portname (str): The name of a port.
        variants (list): The variants to apply to `portname`.

    Returns:
        Graph.Graph: The graph.

    """
    decorate_node_q = Queue()
    thread = ThreadHandler(decorate_node, decorate_node_q)
    thread.start()
    visited = set()
    def traverse(parent):
        """Recursively traverse dependencies to `parent`."""
        if parent in visited:
            return
        else:
            visited.add(parent)
        graph.add_node(parent, {})
        decorate_node_q.put((parent, graph.node_data(parent)))
        for section, child in get_deps(parent.strip('"'), variants):
            if parent is not root:
                graph.node_data(parent)["shape"] = "circle"
            if not child in graph:
                graph.add_node(child, {})
            color = dict(library="black",
                         fetch="forestgreen",
                         extract="darkgreen",
                         build="blue",
                         runtime="red").get(section, "green")
            graph.add_edge(parent, child,
                           edge_data=dict(
                               color=color,
                               fontcolor=color,
                               label=section if section != "library" else "",
                           ),
                           create_nodes=False)
            traverse(child)
    root = portname
    traverse(root)
    decorate_node_q.join()
    return graph


def make_dot(graph):
    """Convert the graph to a dot file.

    Node and edge styles is obtained from the corresponding data.

    Args:
        graph (Graph.Graph): The graph.

    Returns:
        Dot.Dot: The dot file generator.

    """
    dot = Dot.Dot(graph, graphtype="digraph")
    dot.style(overlap=False, bgcolor="transparent")
    node_style = dict(style="filled", fillcolor=Fillcolor.Default,
                      shape="doublecircle")
    for node, (__, __, data) in six.iteritems(graph.nodes):
        style = node_style.copy()
        style.update(data)
        dot.node_style(node, **style)
    for head, tail, style in six.itervalues(graph.edges):
        dot.edge_style(head, tail, **style)
    return dot


def show_stats(graph):
    """Create and display stats from the `graph`."""
    stats = {Fillcolor.Not_Installed: 0,
             Fillcolor.Outdated: 0,
             Fillcolor.Default: 0}
    for __, __, data in six.itervalues(graph.nodes):
        stats[data.get("fillcolor", Fillcolor.Default)] += 1
    print("Total:", graph.number_of_nodes(),
          "(%i" % stats[Fillcolor.Outdated], "upgrades,",
          stats[Fillcolor.Not_Installed], "new)",
          file=sys.stderr)


if __name__ == '__main__':
    graph = Graph.Graph()
    commandline = {}
    try:
        if not sys.argv[1:]:
            raise RuntimeError
        for arg in sys.argv[1:]:
            if arg.startswith("@"):
                continue
            elif not (arg.startswith("+") or arg.startswith("-")):
                portname = arg
                commandline[portname] = []
            else:
                commandline[portname].append(arg)
    except:
        print(__doc__, file=_stdout)
        exit(1)
    for portname, variants in six.iteritems(commandline):
        print("Calculating dependencies for", portname, *variants,
              file=sys.stderr)
        make_graph(portname, variants, graph)
    show_stats(graph)
    for line in make_dot(graph).iterdot():
        print(line, file=_stdout)
    _stdout.flush()
