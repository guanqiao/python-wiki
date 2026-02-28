"""
包分析器模块
提供项目子包检测、依赖分析、架构分层检测等功能
支持 Python、TypeScript、Java 等多语言项目
支持 Java Maven/Gradle 多模块项目结构分析
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pywiki.parsers.factory import ParserFactory


@dataclass
class SubPackageInfo:
    """子包信息"""
    name: str
    path: str
    language: str
    file_count: int
    class_count: int
    function_count: int
    description: str = ""
    responsibilities: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    imports_from: list[str] = field(default_factory=list)
    layer_hint: str = ""


@dataclass
class PackageDependency:
    """包间依赖"""
    source_package: str
    target_package: str
    dependency_type: str
    strength: float = 0.0
    locations: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)


@dataclass
class ArchitectureLayer:
    """架构层"""
    name: str
    packages: list[str]
    description: str = ""
    allowed_dependencies: list[str] = field(default_factory=list)
    violations: list[dict] = field(default_factory=list)


@dataclass
class PackageMetric:
    """包级别指标"""
    package_name: str
    stability: float = 0.0
    abstractness: float = 0.0
    distance: float = 0.0
    coupling: float = 0.0
    cohesion: float = 0.0


@dataclass
class JavaModuleInfo:
    """Java 模块信息（Maven/Gradle 模块）"""
    name: str
    path: str
    module_type: str = "maven"
    group_id: str = ""
    artifact_id: str = ""
    version: str = ""
    parent_module: Optional[str] = None
    sub_modules: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    source_dirs: list[str] = field(default_factory=list)
    test_dirs: list[str] = field(default_factory=list)
    description: str = ""


class PackageAnalyzer:
    """包分析器
    
    提供项目子包检测、依赖分析、架构分层检测等功能。
    支持 Python、TypeScript、Java 等多语言项目。
    支持 Java Maven/Gradle 多模块项目结构分析。
    可被多个 Agent 复用。
    
    Example:
        >>> analyzer = PackageAnalyzer()
        >>> subpackages = analyzer.detect_subpackages(Path("/path/to/project"))
        >>> deps = analyzer.analyze_package_dependencies(subpackages)
    """
    
    LAYER_PATTERNS = {
        "presentation": [
            "ui", "view", "component", "page", "screen", "controller",
            "api", "endpoint", "route", "handler", "web", "http"
        ],
        "business": [
            "service", "usecase", "interactor", "domain", "logic",
            "manager", "processor", "application", "core"
        ],
        "data": [
            "repository", "dao", "model", "entity", "dto", "schema",
            "data", "store", "db", "persistence", "mapper"
        ],
        "infrastructure": [
            "config", "util", "helper", "common", "base",
            "infrastructure", "infra", "shared", "lib"
        ],
    }
    
    LANGUAGE_EXTENSIONS = {
        "python": [".py", ".pyi"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx", ".mjs"],
        "java": [".java"],
    }
    
    EXTENSION_LANGUAGE = {
        ".py": "python",
        ".pyi": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".java": "java",
    }
    
    JAVA_SOURCE_DIRS = [
        "src/main/java",
        "src/test/java",
        "src/main/resources",
        "src/test/resources",
    ]
    
    JAVA_EXCLUDE_DIRS = [
        "target", "build", ".idea", ".mvn", ".gradle",
        "out", "bin", "classes", "generated-sources",
        "generated-test-sources", "maven-status", "surefire-reports",
    ]
    
    JAVA_MODULE_MARKERS = ["pom.xml", "build.gradle", "build.gradle.kts"]
    
    def __init__(
        self,
        parser_factory: Optional[ParserFactory] = None,
        exclude_patterns: Optional[list[str]] = None,
    ):
        """初始化包分析器
        
        Args:
            parser_factory: 解析器工厂实例
            exclude_patterns: 排除的路径模式
        """
        self._parser_factory = parser_factory or ParserFactory()
        default_excludes = [
            "__pycache__", "node_modules", ".git", ".venv", "venv",
            "target", "build", ".idea", ".mvn", ".gradle",
            "out", "bin", "classes", "generated-sources",
            "generated-test-sources", "maven-status", "surefire-reports",
            "test-classes", ".history", ".cache",
        ]
        self._exclude_patterns = exclude_patterns or default_excludes
        self._project_type: Optional[str] = None
        self._is_java_project: bool = False
        self._java_modules: list[JavaModuleInfo] = []
    
    def detect_subpackages(self, project_path: Path) -> list[SubPackageInfo]:
        """检测项目中的子包
        
        Args:
            project_path: 项目根路径
            
        Returns:
            检测到的子包列表
        """
        self._detect_project_type(project_path)
        
        if self._is_java_project:
            return self._detect_java_subpackages(project_path)
        
        return self._detect_general_subpackages(project_path)
    
    def _detect_project_type(self, project_path: Path) -> None:
        """检测项目类型"""
        pom_path = project_path / "pom.xml"
        gradle_path = project_path / "build.gradle"
        gradle_kts_path = project_path / "build.gradle.kts"
        
        if pom_path.exists():
            self._project_type = "maven"
            self._is_java_project = True
        elif gradle_path.exists() or gradle_kts_path.exists():
            self._project_type = "gradle"
            self._is_java_project = True
        elif (project_path / "setup.py").exists() or (project_path / "pyproject.toml").exists():
            self._project_type = "python"
            self._is_java_project = False
        elif (project_path / "package.json").exists():
            self._project_type = "nodejs"
            self._is_java_project = False
        else:
            self._project_type = "unknown"
            self._is_java_project = False
    
    def _detect_java_subpackages(self, project_path: Path) -> list[SubPackageInfo]:
        """检测 Java 项目的子包结构
        
        支持 Maven/Gradle 多模块项目
        """
        subpackages = []
        visited_paths = set()
        
        self._java_modules = self._detect_java_modules(project_path)
        
        if self._java_modules:
            for module in self._java_modules:
                module_packages = self._detect_packages_in_java_module(
                    project_path, module, visited_paths
                )
                subpackages.extend(module_packages)
        else:
            for source_dir in self.JAVA_SOURCE_DIRS:
                src_path = project_path / source_dir
                if src_path.exists():
                    packages = self._detect_java_packages_in_dir(
                        src_path, project_path, visited_paths
                    )
                    subpackages.extend(packages)
        
        return subpackages
    
    def _detect_java_modules(self, project_path: Path) -> list[JavaModuleInfo]:
        """检测 Java 多模块项目结构"""
        modules = []
        
        pom_path = project_path / "pom.xml"
        if pom_path.exists():
            modules.extend(self._parse_maven_modules(pom_path, project_path))
        
        settings_gradle = project_path / "settings.gradle"
        settings_gradle_kts = project_path / "settings.gradle.kts"
        if settings_gradle.exists() or settings_gradle_kts.exists():
            gradle_file = settings_gradle if settings_gradle.exists() else settings_gradle_kts
            modules.extend(self._parse_gradle_modules(gradle_file, project_path))
        
        return modules
    
    def _parse_maven_modules(self, pom_path: Path, project_path: Path) -> list[JavaModuleInfo]:
        """解析 Maven pom.xml 获取模块信息"""
        modules = []
        
        try:
            content = pom_path.read_text(encoding="utf-8")
            
            group_id_match = re.search(r"<groupId>([^<]+)</groupId>", content)
            artifact_id_match = re.search(r"<artifactId>([^<]+)</artifactId>", content)
            version_match = re.search(r"<version>([^<]+)</version>", content)
            description_match = re.search(r"<description>([^<]*)</description>", content)
            
            root_module = JavaModuleInfo(
                name=artifact_id_match.group(1) if artifact_id_match else project_path.name,
                path=".",
                module_type="maven",
                group_id=group_id_match.group(1) if group_id_match else "",
                artifact_id=artifact_id_match.group(1) if artifact_id_match else "",
                version=version_match.group(1) if version_match else "",
                description=description_match.group(1) if description_match else "",
            )
            
            sub_module_matches = re.findall(r"<module>([^<]+)</module>", content)
            for module_name in sub_module_matches:
                module_path = project_path / module_name
                module_pom = module_path / "pom.xml"
                
                if module_path.exists():
                    sub_module = JavaModuleInfo(
                        name=module_name,
                        path=module_name,
                        module_type="maven",
                        parent_module=root_module.name,
                    )
                    
                    if module_pom.exists():
                        try:
                            module_content = module_pom.read_text(encoding="utf-8")
                            content_without_parent = re.sub(r"<parent>.*?</parent>", "", module_content, flags=re.DOTALL)
                            sub_artifact_id = re.search(r"<artifactId>([^<]+)</artifactId>", content_without_parent)
                            sub_description = re.search(r"<description>([^<]*)</description>", content_without_parent)
                            if sub_artifact_id:
                                sub_module.artifact_id = sub_artifact_id.group(1)
                                sub_module.name = sub_artifact_id.group(1)
                            if sub_description:
                                sub_module.description = sub_description.group(1).strip()
                        except Exception:
                            pass
                    
                    root_module.sub_modules.append(module_name)
                    modules.append(sub_module)
            
            modules.insert(0, root_module)
            
        except Exception:
            pass
        
        return modules
    
    def _parse_gradle_modules(self, settings_file: Path, project_path: Path) -> list[JavaModuleInfo]:
        """解析 Gradle settings 文件获取模块信息"""
        modules = []
        
        try:
            content = settings_file.read_text(encoding="utf-8")
            
            root_module = JavaModuleInfo(
                name=project_path.name,
                path=".",
                module_type="gradle",
            )
            
            include_matches = re.findall(r"include\s*['\"]([^'\"]+)['\"]", content)
            include_matches += re.findall(r"include\s*\(['\"]([^'\"]+)['\"]\)", content)
            
            for module_name in include_matches:
                module_name = module_name.replace(":", "").strip()
                if module_name:
                    module_path = project_path / module_name
                    if module_path.exists():
                        sub_module = JavaModuleInfo(
                            name=module_name,
                            path=module_name,
                            module_type="gradle",
                            parent_module=root_module.name,
                        )
                        root_module.sub_modules.append(module_name)
                        modules.append(sub_module)
            
            modules.insert(0, root_module)
            
        except Exception:
            pass
        
        return modules
    
    def _detect_packages_in_java_module(
        self,
        project_path: Path,
        module: JavaModuleInfo,
        visited_paths: set
    ) -> list[SubPackageInfo]:
        """检测 Java 模块中的包结构"""
        packages = []
        module_path = project_path / module.path if module.path != "." else project_path
        
        for source_dir in self.JAVA_SOURCE_DIRS:
            src_path = module_path / source_dir
            if src_path.exists():
                module_packages = self._detect_java_packages_in_dir(
                    src_path, project_path, visited_paths, module.name
                )
                packages.extend(module_packages)
        
        return packages
    
    def _detect_java_packages_in_dir(
        self,
        src_path: Path,
        project_path: Path,
        visited_paths: set,
        module_name: str = ""
    ) -> list[SubPackageInfo]:
        """检测 Java 源目录中的包结构"""
        packages = []
        
        for root, dirs, files in os.walk(src_path):
            root_path = Path(root)
            
            if self._should_exclude(root_path):
                dirs[:] = [d for d in dirs if not self._should_exclude(root_path / d)]
                continue
            
            java_files = [f for f in files if f.endswith(".java")]
            
            if java_files:
                rel_path = root_path.relative_to(src_path)
                
                if str(rel_path) == ".":
                    continue
                
                package_name = str(rel_path).replace(os.sep, ".")
                
                if module_name:
                    full_package_name = f"{module_name}:{package_name}"
                else:
                    full_package_name = package_name
                
                if full_package_name in visited_paths:
                    continue
                visited_paths.add(full_package_name)
                
                subpackage = self._analyze_java_package(
                    root_path, package_name, project_path, module_name, len(java_files)
                )
                if subpackage:
                    packages.append(subpackage)
        
        return packages
    
    def _analyze_java_package(
        self,
        package_path: Path,
        package_name: str,
        project_path: Path,
        module_name: str = "",
        file_count: int = 0
    ) -> Optional[SubPackageInfo]:
        """分析单个 Java 包"""
        class_count = 0
        function_count = 0
        exports = []
        imports_from = []
        
        for file_path in package_path.glob("*.java"):
            if self._should_exclude(file_path):
                continue
            
            parser = self._parser_factory.get_parser(file_path)
            if parser:
                try:
                    module = parser.parse_file(file_path)
                    if module:
                        class_count += len(module.classes)
                        function_count += len(module.functions)
                        
                        for cls in module.classes:
                            if not cls.name.startswith("_"):
                                exports.append(cls.name)
                        
                        for func in module.functions:
                            if not func.name.startswith("_"):
                                exports.append(func.name)
                        
                        for imp in module.imports:
                            if imp.module and imp.module not in imports_from:
                                imports_from.append(imp.module)
                except Exception:
                    pass
        
        if file_count == 0 and class_count == 0:
            return None
        
        layer_hint = self._detect_layer_hint(package_name, exports)
        
        display_name = f"{module_name}:{package_name}" if module_name else package_name
        
        return SubPackageInfo(
            name=display_name,
            path=str(package_path.relative_to(project_path)),
            language="java",
            file_count=file_count,
            class_count=class_count,
            function_count=function_count,
            exports=exports[:50],
            imports_from=imports_from[:30],
            layer_hint=layer_hint,
        )
    
    def _detect_general_subpackages(self, project_path: Path) -> list[SubPackageInfo]:
        """检测通用项目的子包结构（Python/TypeScript 等）"""
        subpackages = []
        visited_paths = set()
        
        source_dirs = ["src", "lib", "app", project_path.name]
        
        for source_dir in source_dirs:
            src_path = project_path / source_dir
            if not src_path.exists():
                continue
            
            for root, dirs, files in os.walk(src_path):
                root_path = Path(root)
                
                if self._should_exclude(root_path):
                    continue
                
                init_files = [
                    f for f in files 
                    if f in ("__init__.py", "index.ts", "index.js")
                ]
                has_code_files = any(
                    f.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".java"))
                    for f in files
                )
                
                if init_files or (has_code_files and root_path != src_path):
                    rel_path = root_path.relative_to(project_path)
                    package_name = str(rel_path).replace(os.sep, ".")
                    
                    if package_name in visited_paths:
                        continue
                    visited_paths.add(package_name)
                    
                    subpackage = self._analyze_single_package(
                        root_path, package_name, project_path
                    )
                    if subpackage:
                        subpackages.append(subpackage)
        
        return subpackages
    
    def _should_exclude(self, path: Path) -> bool:
        """检查路径是否应该被排除"""
        path_str = str(path)
        for pattern in self._exclude_patterns:
            if pattern in path_str:
                return True
        return False
    
    def _analyze_single_package(
        self,
        package_path: Path,
        package_name: str,
        project_path: Path
    ) -> Optional[SubPackageInfo]:
        """分析单个子包"""
        file_count = 0
        class_count = 0
        function_count = 0
        exports = []
        imports_from = []
        language_counts = {}
        
        for ext in [".py", ".ts", ".tsx", ".js", ".jsx", ".java"]:
            for file_path in package_path.glob(f"*{ext}"):
                if self._should_exclude(file_path):
                    continue
                
                file_count += 1
                language = self.EXTENSION_LANGUAGE.get(ext, "unknown")
                language_counts[language] = language_counts.get(language, 0) + 1
                
                parser = self._parser_factory.get_parser(file_path)
                if parser:
                    try:
                        module = parser.parse_file(file_path)
                        if module:
                            class_count += len(module.classes)
                            function_count += len(module.functions)
                            
                            for cls in module.classes:
                                if not cls.name.startswith("_"):
                                    exports.append(cls.name)
                            
                            for func in module.functions:
                                if not func.name.startswith("_"):
                                    exports.append(func.name)
                            
                            for imp in module.imports:
                                if imp.module and imp.module not in imports_from:
                                    imports_from.append(imp.module)
                    except Exception:
                        pass
        
        if file_count == 0:
            return None
        
        dominant_language = (
            max(language_counts.items(), key=lambda x: x[1])[0]
            if language_counts else "unknown"
        )
        
        layer_hint = self._detect_layer_hint(package_name, exports)
        
        return SubPackageInfo(
            name=package_name,
            path=str(package_path.relative_to(project_path)),
            language=dominant_language,
            file_count=file_count,
            class_count=class_count,
            function_count=function_count,
            exports=exports[:50],
            imports_from=imports_from[:30],
            layer_hint=layer_hint,
        )
    
    def _detect_layer_hint(self, package_name: str, exports: list[str]) -> str:
        """检测包可能属于的架构层"""
        name_lower = package_name.lower()
        
        for layer, patterns in self.LAYER_PATTERNS.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return layer
        
        for export in exports:
            export_lower = export.lower()
            for layer, patterns in self.LAYER_PATTERNS.items():
                for pattern in patterns:
                    if pattern in export_lower:
                        return layer
        
        return ""
    
    def analyze_package_dependencies(
        self,
        subpackages: list[SubPackageInfo]
    ) -> list[PackageDependency]:
        """分析包间依赖
        
        Args:
            subpackages: 子包列表
            
        Returns:
            包依赖列表
        """
        package_names = {sp.name for sp in subpackages}
        dependencies = []
        dependency_matrix = {}
        
        for sp in subpackages:
            dependency_matrix[sp.name] = {}
            
            for imp_module in sp.imports_from:
                matched_package = self._find_matching_package(imp_module, package_names)
                
                if matched_package and matched_package != sp.name:
                    dep_key = f"{sp.name}->{matched_package}"
                    
                    if dep_key not in dependency_matrix[sp.name]:
                        dependency_matrix[sp.name][dep_key] = PackageDependency(
                            source_package=sp.name,
                            target_package=matched_package,
                            dependency_type="import",
                            strength=0.0,
                            locations=[],
                            entities=[],
                        )
                    
                    dependency_matrix[sp.name][dep_key].locations.append(sp.path)
        
        for pkg_deps in dependency_matrix.values():
            for dep in pkg_deps.values():
                dep.strength = min(1.0, len(dep.locations) / 5.0)
                dependencies.append(dep)
        
        return dependencies
    
    def _find_matching_package(
        self,
        import_module: str,
        package_names: set[str]
    ) -> Optional[str]:
        """查找导入模块对应的包"""
        parts = import_module.split(".")
        
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in package_names:
                return candidate
        
        return None
    
    def detect_circular_dependencies(
        self,
        dependencies: list[PackageDependency]
    ) -> list[list[str]]:
        """检测循环依赖
        
        Args:
            dependencies: 包依赖列表
            
        Returns:
            循环依赖列表
        """
        graph = {}
        
        for dep in dependencies:
            if dep.source_package not in graph:
                graph[dep.source_package] = []
            graph[dep.source_package].append(dep.target_package)
        
        circular = []
        visited = set()
        
        def dfs(node: str, path: list[str]):
            if node in path:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if cycle not in circular:
                    circular.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path.copy())
        
        for node in graph:
            dfs(node, [])
        
        return circular
    
    def detect_layered_architecture(
        self,
        subpackages: list[SubPackageInfo]
    ) -> list[ArchitectureLayer]:
        """检测分层架构
        
        Args:
            subpackages: 子包列表
            
        Returns:
            架构层列表
        """
        layers = [
            ArchitectureLayer(
                name="presentation",
                packages=[],
                description="表示层 - 处理用户交互和API端点",
                allowed_dependencies=["business", "infrastructure"],
            ),
            ArchitectureLayer(
                name="business",
                packages=[],
                description="业务层 - 核心业务逻辑",
                allowed_dependencies=["data", "infrastructure"],
            ),
            ArchitectureLayer(
                name="data",
                packages=[],
                description="数据层 - 数据存储和访问",
                allowed_dependencies=["infrastructure"],
            ),
            ArchitectureLayer(
                name="infrastructure",
                packages=[],
                description="基础设施层 - 通用工具和配置",
                allowed_dependencies=[],
            ),
        ]
        
        layer_map = {layer.name: layer for layer in layers}
        
        for sp in subpackages:
            if sp.layer_hint and sp.layer_hint in layer_map:
                layer_map[sp.layer_hint].packages.append(sp.name)
        
        return [layer for layer in layers if layer.packages]
    
    def analyze_package_boundaries(
        self,
        subpackages: list[SubPackageInfo],
        layers: Optional[list[ArchitectureLayer]] = None
    ) -> list[dict]:
        """分析包边界违规
        
        Args:
            subpackages: 子包列表
            layers: 架构层列表（可选）
            
        Returns:
            边界违规列表
        """
        if layers is None:
            layers = self.detect_layered_architecture(subpackages)
        
        violations = []
        package_names = {sp.name for sp in subpackages}
        
        for layer in layers:
            for pkg in layer.packages:
                sp = next((s for s in subpackages if s.name == pkg), None)
                if not sp:
                    continue
                
                for imp_module in sp.imports_from:
                    for other_layer in layers:
                        if other_layer.name in layer.allowed_dependencies:
                            continue
                        
                        if any(
                            imp_module.startswith(p) or
                            self._find_matching_package(imp_module, package_names) in other_layer.packages
                            for p in other_layer.packages
                        ):
                            violations.append({
                                "source_package": pkg,
                                "source_layer": layer.name,
                                "target_module": imp_module,
                                "target_layer": other_layer.name,
                                "violation_type": "layer_violation",
                            })
        
        return violations
    
    def calculate_package_metrics(
        self,
        subpackages: list[SubPackageInfo],
        dependencies: Optional[list[PackageDependency]] = None
    ) -> list[PackageMetric]:
        """计算包级别指标
        
        Args:
            subpackages: 子包列表
            dependencies: 包依赖列表（可选）
            
        Returns:
            包指标列表
        """
        if dependencies is None:
            dependencies = self.analyze_package_dependencies(subpackages)
        
        afferent_coupling = {}
        efferent_coupling = {}
        
        for dep in dependencies:
            target = dep.target_package
            source = dep.source_package
            if target:
                afferent_coupling[target] = afferent_coupling.get(target, 0) + 1
            if source:
                efferent_coupling[source] = efferent_coupling.get(source, 0) + 1
        
        metrics = []
        
        for sp in subpackages:
            ca = afferent_coupling.get(sp.name, 0)
            ce = efferent_coupling.get(sp.name, 0)
            total_coupling = ca + ce
            
            stability = ca / total_coupling if total_coupling > 0 else 0.0
            
            abstract_count = sum(
                1 for e in sp.exports
                if e[0].isupper() and not e.isupper()
            )
            abstractness = abstract_count / sp.class_count if sp.class_count > 0 else 0.0
            
            distance = abs(abstractness + stability - 1)
            
            coupling = ce / total_coupling if total_coupling > 0 else 0.0
            
            cohesion = 1.0 - coupling
            
            metrics.append(PackageMetric(
                package_name=sp.name,
                stability=round(stability, 3),
                abstractness=round(abstractness, 3),
                distance=round(distance, 3),
                coupling=round(coupling, 3),
                cohesion=round(cohesion, 3),
            ))
        
        return metrics
    
    def build_package_tree(
        self,
        subpackages: list[SubPackageInfo]
    ) -> dict:
        """构建包树结构
        
        Args:
            subpackages: 子包列表
            
        Returns:
            包树结构
        """
        tree = {}
        
        for sp in subpackages:
            if ":" in sp.name:
                module_part, package_part = sp.name.split(":", 1)
                parts = [module_part] + package_part.split(".")
            else:
                parts = sp.name.split(".")
            
            current = tree
            
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {
                        "_info": None,
                        "_children": {},
                    }
                
                if i == len(parts) - 1:
                    current[part]["_info"] = {
                        "file_count": sp.file_count,
                        "language": sp.language,
                        "layer_hint": sp.layer_hint,
                    }
                else:
                    current = current[part]["_children"]
        
        return tree
    
    def analyze_layer_distribution(
        self,
        subpackages: list[SubPackageInfo]
    ) -> dict[str, list[str]]:
        """分析层分布
        
        Args:
            subpackages: 子包列表
            
        Returns:
            层分布字典
        """
        distribution = {
            "presentation": [],
            "business": [],
            "data": [],
            "infrastructure": [],
            "unknown": [],
        }
        
        for sp in subpackages:
            if sp.layer_hint:
                distribution[sp.layer_hint].append(sp.name)
            else:
                distribution["unknown"].append(sp.name)
        
        return distribution
    
    def get_full_analysis(self, project_path: Path) -> dict[str, Any]:
        """获取完整的包分析结果
        
        Args:
            project_path: 项目根路径
            
        Returns:
            完整分析结果
        """
        subpackages = self.detect_subpackages(project_path)
        dependencies = self.analyze_package_dependencies(subpackages)
        circular_deps = self.detect_circular_dependencies(dependencies)
        layers = self.detect_layered_architecture(subpackages)
        violations = self.analyze_package_boundaries(subpackages, layers)
        metrics = self.calculate_package_metrics(subpackages, dependencies)
        package_tree = self.build_package_tree(subpackages)
        layer_distribution = self.analyze_layer_distribution(subpackages)
        
        result = {
            "subpackages": [
                {
                    "name": sp.name,
                    "path": sp.path,
                    "language": sp.language,
                    "file_count": sp.file_count,
                    "class_count": sp.class_count,
                    "function_count": sp.function_count,
                    "exports": sp.exports[:20],
                    "imports_from": sp.imports_from[:10],
                    "layer_hint": sp.layer_hint,
                }
                for sp in subpackages
            ],
            "total_subpackages": len(subpackages),
            "dependencies": [
                {
                    "source": d.source_package,
                    "target": d.target_package,
                    "type": d.dependency_type,
                    "strength": d.strength,
                    "location_count": len(d.locations),
                }
                for d in dependencies
            ],
            "circular_dependencies": circular_deps,
            "layers": [
                {
                    "name": layer.name,
                    "packages": layer.packages,
                    "description": layer.description,
                    "allowed_dependencies": layer.allowed_dependencies,
                }
                for layer in layers
            ],
            "violations": violations,
            "metrics": [
                {
                    "package": m.package_name,
                    "stability": m.stability,
                    "abstractness": m.abstractness,
                    "distance": m.distance,
                    "coupling": m.coupling,
                    "cohesion": m.cohesion,
                }
                for m in metrics
            ],
            "package_tree": package_tree,
            "layer_distribution": layer_distribution,
            "summary": {
                "total_packages": len(subpackages),
                "total_dependencies": len(dependencies),
                "circular_dependency_count": len(circular_deps),
                "layer_violation_count": len(violations),
                "avg_stability": sum(m.stability for m in metrics) / len(metrics) if metrics else 0,
                "avg_cohesion": sum(m.cohesion for m in metrics) / len(metrics) if metrics else 0,
            },
        }
        
        if self._is_java_project and self._java_modules:
            result["java_modules"] = [
                {
                    "name": m.name,
                    "path": m.path,
                    "module_type": m.module_type,
                    "group_id": m.group_id,
                    "artifact_id": m.artifact_id,
                    "version": m.version,
                    "parent_module": m.parent_module,
                    "sub_modules": m.sub_modules,
                    "description": m.description,
                }
                for m in self._java_modules
            ]
            result["project_type"] = self._project_type
        
        return result
    
    def get_java_module_structure(self, project_path: Path) -> dict[str, Any]:
        """获取 Java 模块结构信息
        
        Args:
            project_path: 项目根路径
            
        Returns:
            Java 模块结构信息
        """
        self._detect_project_type(project_path)
        
        if not self._is_java_project:
            return {"is_java_project": False}
        
        self._java_modules = self._detect_java_modules(project_path)
        
        module_tree = {}
        for module in self._java_modules:
            module_info = {
                "name": module.name,
                "path": module.path,
                "type": module.module_type,
                "group_id": module.group_id,
                "artifact_id": module.artifact_id,
                "version": module.version,
                "description": module.description,
                "sub_modules": [],
                "packages": [],
            }
            
            module_path = project_path / module.path if module.path != "." else project_path
            for source_dir in self.JAVA_SOURCE_DIRS:
                src_path = module_path / source_dir
                if src_path.exists():
                    for root, dirs, files in os.walk(src_path):
                        root_path = Path(root)
                        if self._should_exclude(root_path):
                            continue
                        
                        java_files = [f for f in files if f.endswith(".java")]
                        if java_files:
                            rel_path = root_path.relative_to(src_path)
                            if str(rel_path) != ".":
                                package_name = str(rel_path).replace(os.sep, ".")
                                module_info["packages"].append(package_name)
            
            if module.parent_module:
                parent = next(
                    (m for m in module_tree.values() if m["name"] == module.parent_module),
                    None
                )
                if parent:
                    parent["sub_modules"].append(module_info)
                else:
                    module_tree[module.name] = module_info
            else:
                module_tree[module.name] = module_info
        
        return {
            "is_java_project": True,
            "project_type": self._project_type,
            "modules": list(module_tree.values()),
            "total_modules": len(self._java_modules),
        }
