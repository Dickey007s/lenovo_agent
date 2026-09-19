(function (root) {
  function select(sources, kind = 'all', query = '') {
    const needle = query.trim().toLocaleLowerCase();
    return sources.filter(s => {
      const official = s.type.startsWith('official_');
      return (kind === 'all' || (kind === 'official' ? official : !official)) &&
        [s.title,s.source_claim,s.design_inference,s.testable_counterexample,s.id].join(' ').toLocaleLowerCase().includes(needle);
    }).sort((a,b)=>a.priority-b.priority || Number(a.type.startsWith('official_'))-Number(b.type.startsWith('official_')) || a.id.localeCompare(b.id));
  }
  const api = {select};
  if(typeof module !== 'undefined') module.exports=api;
  else root.BoundaryResearchView=api;
})(typeof window !== 'undefined' ? window : this);
