"""
Mermaid 图表生成器模块
"""

from pywiki.generators.diagrams.base import BaseDiagramGenerator
from pywiki.generators.diagrams.architecture import (
    ArchitectureDiagramGenerator,
    ArchitectureStyle,
    ComponentType,
    ArchitectureComponent,
    ArchitectureLayer,
)
from pywiki.generators.diagrams.flowchart import FlowchartGenerator
from pywiki.generators.diagrams.sequence import SequenceDiagramGenerator
from pywiki.generators.diagrams.class_diagram import ClassDiagramGenerator
from pywiki.generators.diagrams.state import StateDiagramGenerator
from pywiki.generators.diagrams.er_diagram import ERDiagramGenerator
from pywiki.generators.diagrams.component import ComponentDiagramGenerator
from pywiki.generators.diagrams.db_schema import DBSchemaGenerator
from pywiki.generators.diagrams.c4_diagrams import (
    C4ContextDiagramGenerator,
    C4ContainerDiagramGenerator,
    C4ComponentDiagramGenerator,
    C4CodeDiagramGenerator,
    C4DiagramGenerator,
    C4Level,
    C4Person,
    C4System,
    C4Container,
    C4Component,
    C4Relationship,
)
from pywiki.generators.diagrams.dataflow import (
    DataFlowDiagramGenerator,
    DataFlowNodeType,
    DataFlowNode,
    DataFlow,
    DataFlowDiagram,
)
from pywiki.generators.diagrams.microservice import (
    MicroserviceDiagramGenerator,
    ServiceType,
    CommunicationPattern,
    MicroserviceNode,
    ServiceConnection,
)
from pywiki.generators.diagrams.deployment_diagram import (
    DeploymentDiagramGenerator,
    NodeType,
    Environment,
    DeploymentNode,
    NetworkConnection,
)
from pywiki.generators.diagrams.package_diagram import (
    PackageDiagramGenerator,
    DependencyType,
    PackageType,
    PackageNode,
    DependencyEdge,
)

__all__ = [
    "BaseDiagramGenerator",
    # Architecture
    "ArchitectureDiagramGenerator",
    "ArchitectureStyle",
    "ComponentType",
    "ArchitectureComponent",
    "ArchitectureLayer",
    # Basic diagrams
    "FlowchartGenerator",
    "SequenceDiagramGenerator",
    "ClassDiagramGenerator",
    "StateDiagramGenerator",
    "ERDiagramGenerator",
    "ComponentDiagramGenerator",
    "DBSchemaGenerator",
    # C4 Model
    "C4ContextDiagramGenerator",
    "C4ContainerDiagramGenerator",
    "C4ComponentDiagramGenerator",
    "C4CodeDiagramGenerator",
    "C4DiagramGenerator",
    "C4Level",
    "C4Person",
    "C4System",
    "C4Container",
    "C4Component",
    "C4Relationship",
    # Data Flow
    "DataFlowDiagramGenerator",
    "DataFlowNodeType",
    "DataFlowNode",
    "DataFlow",
    "DataFlowDiagram",
    # Microservice
    "MicroserviceDiagramGenerator",
    "ServiceType",
    "CommunicationPattern",
    "MicroserviceNode",
    "ServiceConnection",
    # Deployment
    "DeploymentDiagramGenerator",
    "NodeType",
    "Environment",
    "DeploymentNode",
    "NetworkConnection",
    # Package
    "PackageDiagramGenerator",
    "DependencyType",
    "PackageType",
    "PackageNode",
    "DependencyEdge",
]
