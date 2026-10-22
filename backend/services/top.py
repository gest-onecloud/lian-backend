from .calendar import matches
def top(repo,date):
 ms=[m for m in matches(repo,date) if m.get('selection_eligible')]
 return sorted(ms,key=lambda m:(m.get('evidence',0)*m.get('confidence',0),max(m.get('probabilities',{}).values() or [0])),reverse=True)[:10]
