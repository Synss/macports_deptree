#!/usr/bin/env python
# Copyright (c) 2014, Mathias Laurin
# BSD 3-Clause License (http://opensource.org/licenses/BSD-3-Clause)

"""Print all dependencies required to build a port as a graph.

Usage:
    port_deptree.py PORTNAME [VARIANTS ...]

Example:
    port_deptree.py irssi -perl | dot -Tpdf -oirssi.pdf
    port_deptree.py $(port echo requested and outdated)\
            | dot -Tpdf | open -fa Preview

"""
from __future__ import print_function
import sys
import subprocess
import threading
from Queue import Queue
import pydot
__version__ = "0.5"


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


def is_installed(portname):
    """Return True if `portname` is installed, False otherwise."""
    process = ["port", "installed", portname]
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        return not line.startswith("None")


def is_outdated(portname):
    """Return True if `portname` is outdated, False otherwise."""
    process = ["port", "outdated", portname]
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        return not line.startswith("No")


def get_deps(portname, variants):
    """Return `section, depname` dependents of `portname` with `variants`."""
    process = ["port", "deps", portname]
    process.extend(variants)
    for line in subprocess.Popen(
            process, stdout=subprocess.PIPE).stdout.readlines():
        section, sep, children = line.partition(":")
        if not section.endswith("Dependencies"): continue
        for child in [child.strip() for child in children.split(",")]:
            yield section.split()[0].lower(), child


def decorate_node(node):
    """Color `node` if it is outdated or not installed."""
    portname = node.get_name().strip('"')
    if not is_installed(portname):
        node.set_fillcolor("moccasin")
        node.set_color("red")
    elif is_outdated(portname):
        node.set_fillcolor("lightblue")
        node.set_color("forestgreen")


def make_tree(portname, variants, graph):
    """Traverse dependency tree of `portname` with `variants`.

    Args:
        portname (str): The name of a port.
        variants (list): The variants to apply to `portname`.

    Returns:
        pydot.Dot: The graph.

    """
    decorate_node_q = Queue()
    thread = ThreadHandler(decorate_node, decorate_node_q)
    thread.start()
    def traverse(parent):
        """Recursively traverse dependencies to `parent`."""
        if parent.get_name() in (node.get_name() for node in graph.get_nodes()):
            return
        else:
            graph.add_node(parent)
        decorate_node_q.put(parent)
        for section, portname in get_deps(
                parent.get_name().strip('"'), variants):
            child = pydot.Node(portname)
            if parent is not root:
                parent.set_shape("circle")
            edge = pydot.Edge(parent, child)
            color = dict(library="black",
                         fetch="forestgreen",
                         extract="darkgreen",
                         build="blue",
                         runtime="red").get(section, "green")
            if not section == "library":
                edge.set_label(section)
            edge.set_color(color)
            edge.set_fontcolor(color)
            graph.add_edge(edge)
            traverse(child)
    root = pydot.Node(portname)
    traverse(root)
    decorate_node_q.join()
    return graph


if __name__ == '__main__':
    graph = pydot.Dot(graph_type="digraph",
                      overlap=False,
                      bgcolor="transparent")
    graph.set_node_defaults(style="filled", fillcolor="white",
                            shape="doublecircle")
    commandline = {}
    for arg in sys.argv[1:]:
        if arg.startswith("@"):
            continue
        elif not (arg.startswith("+") or arg.startswith("-")):
            portname = arg
            commandline[portname] = []
        else:
            commandline[portname].append(arg)
    for portname, variants in commandline.iteritems():
        print("Calculating dependencies for", portname, *variants,
              file=sys.stderr)
        make_tree(portname, variants, graph)
    print(graph.to_string(), file=sys.stdout)
