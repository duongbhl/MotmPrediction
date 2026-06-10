import { useState, useEffect } from 'react'

const selectCls = [
  'w-full appearance-none bg-white/[0.035] border border-white/[0.06] rounded-[10px]',
  'text-text font-semibold text-sm px-3.5 pr-10 py-3.5 cursor-pointer',
  'transition-all duration-200 focus:outline-none focus:border-green focus:ring-2 focus:ring-green/10',
  "[background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%234E5E72'/%3E%3C/svg%3E\")]",
  '[background-repeat:no-repeat] [background-position:right_14px_center]',
].join(' ')

const scoreInputCls = [
  'w-[54px] h-[54px] bg-white/[0.04] border border-white/[0.06] rounded-[10px]',
  'text-text text-[22px] font-black text-center',
  'transition-all duration-200 focus:outline-none focus:border-green focus:ring-2 focus:ring-green/10',
].join(' ')

export default function MatchSetup({
  homeTeam, awayTeam, homeScore, awayScore,
  onHomeTeam, onAwayTeam, onHomeScore, onAwayScore,
}) {
  const [teams, setTeams] = useState([])

  useEffect(() => {
    fetch('/api/teams')
      .then(r => r.json())
      .then(d => setTeams(d.teams))
      .catch(() => setTeams([
        'Arsenal','Aston Villa','Bournemouth','Brentford','Brighton',
        'Chelsea','Crystal Palace','Everton','Fulham','Ipswich',
        'Liverpool','Man City','Man Utd','Newcastle','Nottingham Forest',
        'Southampton','Tottenham','West Ham','Wolves',
      ]))
  }, [])

  return (
    <div className="bg-card border border-white/[0.06] hover:border-white/[0.12] rounded-[14px] transition-colors mb-5">
      {/* Card header */}
      <div className="flex items-center gap-2.5 px-[22px] pt-[18px] mb-[18px]">
        <div className="w-[30px] h-[30px] rounded-[8px] bg-green/10 flex items-center justify-center text-[15px]">🏟️</div>
        <span className="text-[11px] font-bold tracking-[1.8px] uppercase text-dim">Match Setup</span>
      </div>

      {/* Body */}
      <div className="px-[22px] pb-[22px]">
        <div className="grid grid-cols-[1fr_140px_1fr] gap-[18px] items-end max-[700px]:grid-cols-1">

          {/* Home team */}
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-bold tracking-[2px] uppercase text-muted">Home Team</label>
            <select className={selectCls} value={homeTeam} onChange={e => onHomeTeam(e.target.value)}>
              <option value="">Select team…</option>
              {teams.map(t => <option key={t} value={t} className="bg-[#111B2B]">{t}</option>)}
            </select>
          </div>

          {/* Score */}
          <div className="flex flex-col items-center gap-2 pb-0.5">
            <span className="text-[13px] font-black text-muted tracking-[3px]">VS</span>
            <div className="flex items-center gap-2">
              <input type="number" min={0} max={20} className={scoreInputCls}
                value={homeScore} onChange={e => onHomeScore(Number(e.target.value))} />
              <span className="text-lg font-bold text-muted">—</span>
              <input type="number" min={0} max={20} className={scoreInputCls}
                value={awayScore} onChange={e => onAwayScore(Number(e.target.value))} />
            </div>
          </div>

          {/* Away team */}
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-bold tracking-[2px] uppercase text-muted">Away Team</label>
            <select className={selectCls} value={awayTeam} onChange={e => onAwayTeam(e.target.value)}>
              <option value="">Select team…</option>
              {teams.map(t => <option key={t} value={t} className="bg-[#111B2B]">{t}</option>)}
            </select>
          </div>

        </div>
      </div>
    </div>
  )
}

