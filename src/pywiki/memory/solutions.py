
"""
问题解决方案库
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict


@dataclass
class Solution:
    """解决方案记录"""
    id: str
    problem: str
    solution: str
    tags: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    related_modules: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success_count: int = 0
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


class SolutionMemory:
    """解决方案库管理器"""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._solutions: Dict[str, Solution] = {}
        self._load_solutions()

    def _get_solutions_path(self) -&gt; Path:
        return self.storage_path / "solutions.json"

    def _load_solutions(self) -&gt; None:
        solutions_path = self._get_solutions_path()
        if solutions_path.exists():
            try:
                with open(solutions_path, "r", encoding="utf-8") as f:
                    data_list = json.load(f)
                    self._solutions = {
                        d["id"]: Solution(**d)
                        for d in data_list
                    }
            except Exception:
                self._solutions = {}
        else:
            self._solutions = {}

    def _save_solutions(self) -&gt; None:
        solutions_path = self._get_solutions_path()
        data_list = [asdict(sol) for sol in self._solutions.values()]
        with open(solutions_path, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)

    def _generate_id(self) -&gt; str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"SOL-{timestamp}"

    def add_solution(
        self,
        problem: str,
        solution: str,
        tags: Optional[List[str]] = None,
        related_files: Optional[List[str]] = None,
        related_modules: Optional[List[str]] = None,
        solution_id: Optional[str] = None,
    ) -&gt; Solution:
        """添加解决方案"""
        sol_id = solution_id or self._generate_id()
        sol = Solution(
            id=sol_id,
            problem=problem,
            solution=solution,
            tags=tags or [],
            related_files=related_files or [],
            related_modules=related_modules or [],
        )
        
        self._solutions[sol_id] = sol
        self._save_solutions()
        return sol

    def get_solution(self, solution_id: str) -&gt; Optional[Solution]:
        """获取解决方案"""
        return self._solutions.get(solution_id)

    def update_solution(self, solution_id: str, **kwargs: Any) -&gt; bool:
        """更新解决方案"""
        sol = self._solutions.get(solution_id)
        if not sol:
            return False
        
        for key, value in kwargs.items():
            if hasattr(sol, key):
                setattr(sol, key, value)
        
        self._save_solutions()
        return True

    def increment_success_count(self, solution_id: str) -&gt; bool:
        """增加成功计数"""
        sol = self._solutions.get(solution_id)
        if sol:
            sol.success_count += 1
            self._save_solutions()
            return True
        return False

    def delete_solution(self, solution_id: str) -&gt; bool:
        """删除解决方案"""
        if solution_id in self._solutions:
            del self._solutions[solution_id]
            self._save_solutions()
            return True
        return False

    def search_solutions(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -&gt; List[Solution]:
        """搜索解决方案"""
        results = []
        query_lower = query.lower()
        
        for sol in self._solutions.values():
            if tags and not any(tag in sol.tags for tag in tags):
                continue
            
            if (query_lower in sol.problem.lower() or 
                query_lower in sol.solution.lower() or
                any(query_lower in tag.lower() for tag in sol.tags)):
                results.append(sol)
        
        results.sort(key=lambda x: x.success_count, reverse=True)
        return results[:limit]

    def list_all_solutions(self) -&gt; List[Solution]:
        """列出所有解决方案"""
        return list(self._solutions.values())

    def get_solutions_by_tag(self, tag: str) -&gt; List[Solution]:
        """按标签获取解决方案"""
        return [sol for sol in self._solutions.values() if tag in sol.tags]

    def get_all_tags(self) -&gt; List[str]:
        """获取所有标签"""
        tags = set()
        for sol in self._solutions.values():
            tags.update(sol.tags)
        return sorted(list(tags))
