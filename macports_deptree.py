#!/usr/bin/env python
# Copyright (c) 2014, Mathias Laurin
# BSD 3-Clause License (http://opensource.org/licenses/BSD-3-Clause)

"""Print all dependencies required to build a port as a graph."""

import subprocess
import pydot
__version__ = "0.1"

def make_tree(root, variants):
    cache = set()
    graph = pydot.Dot(graph_type="digraph",
                      overlap=False,
                      bgcolor="transparent")
    graph.add_node(pydot.Node(root, shape="hexagon"))
    def traverse(parent):
        if parent in cache: return
        cache.add(parent)
        process = ["port", "deps", parent]
        process.extend(variants)
        for line in subprocess.Popen(process,
                                     stdout=subprocess.PIPE).stdout.readlines():
            section, sep, children = line.partition(":")
            if not section.endswith("Dependencies"): continue
            for child in [child.strip() for child in children.split(",")]:
                edge = pydot.Edge(parent, child)
                label = section.split()[0].lower()
                color = dict(library="black",
                             extract="darkgreen",
                             build="blue",
                             runtime="red").get(label, "green")
                if not label == "library":
                    edge.set_label(label)
                edge.set_color(color)
                edge.set_fontcolor(color)
                graph.add_edge(edge)
                traverse(child)
    traverse(root)
    return graph

if __name__ == '__main__':
    import sys
    portname = sys.argv[1]
    variants = sys.argv[2:]
    make_tree(portname, variants).write_pdf("%s.pdf" % portname)


