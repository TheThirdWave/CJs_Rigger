import os
import logging

class ComponentGraph():
    
    def __init__(self):
        #The actual graph of nodes.
        self.nodes = []
        #A flat list of all the nodes.
        self.components = []

    @classmethod
    def buildFromList(cls, componentList):
        inst = cls()
        for component in componentList:
            inst.addToList(component)
        for node in inst.nodes:
            inst.findChildren(node)
        inst.deleteNonRootsFromList()
        return inst

    def addToList(self, component):
        if self.checkInList(component):
            return
        newNode = GraphNode(component)
        self.nodes.append(newNode)
        self.components.append(newNode)
                

    def checkInList(self, component):
        for node in self.nodes:
            result = self.checkInTree(component, node)
            if result:
                return result
        return False

    def checkInTree(self, component, node):
        if self.isComponent(component.name, component.prefix, node.component):
            return node.component
        for child in node.children: 
            result = self.checkInTree(component, child)
            if result:
                return result
        return False
    
    def findChildren(self, curnode):
        for child in curnode.component.children:
            for node in self.nodes:
                if self.isComponent(child['childName'], child['childPrefix'], node.component):
                    node.parent.append(curnode)
                    curnode.children.append(node)

    def deleteNonRootsFromList(self):
        for node in list(self.nodes):
            if node.parent:
                self.nodes.remove(node)

    def isComponent(self, cName, cPrefix, checkNodeData):
        if cName == checkNodeData.name and checkNodeData.prefix in cPrefix:
            return True
        return False


class ComponentGraphIterator():
    
    def breadthFirstIteration(self, graph, function):
        # Base Case
        if graph is None:
            return
    
        # Create an empty queue
        # for level order traversal
        queue = []
    
        # Enqueue Root and initialize height
        for node in graph.nodes:
            queue.append(node)
    
        while(len(queue) > 0):
    
            # Call function to be used on component
            # remove it from queue
            if not queue[0].read:
                function(queue[0].component)
            node = queue.pop(0)
            node.read = True
    
            for child in node.children:
                if not child.read:
                    queue.append(child)
        for node in graph.components:
            node.read = False

    def listIteration(self, graph, function):
        for node in graph.components:
            function(node.component)


class GraphNode():

    def __init__(self, component):
        self.parent = []
        self.component = component
        self.children = []
        self.read = False