import { useState } from 'react'
import { initials, posGroup } from '../utils/player'

const POS_STYLES = {
  GK:  'bg-gold/10 text-gold',
  DEF: 'bg-blue/10 text-blue',
  MID: 'bg-green/10 text-green',
  FWD: 'bg-red/10 text-red',
}

export default function LineupPanel({ side, team, players, setPlayers, onAddManual }) {
  const [expanded, setExpanded] = useState(false)
  const isHome = side === 'home'
  const visiblePlayers = expanded ? players : players.slice(0, 8)

  const removePlayer = (index) => {
    const player = visiblePlayers[index]
    setPlayers(prev => prev.filter(item => item !== player))
  }

  return (
    <div className="bg-card border border-white/[0.06] hover:border-white/[0.12] rounded-[14px] transition-colors">
      <div className="flex items-center gap-2.5 px-[22px] pt-[18px] mb-[14px]">
        <div className={`w-[30px] h-[30px] rounded-[8px] flex items-center justify-center text-[15px] ${isHome ? 'bg-green/10' : 'bg-blue/10'}`}>
          {isHome ? '🏠' : '✈️'}
        </div>
        <div className="flex-1">
          <div className="text-[11px] font-bold tracking-[1.8px] uppercase text-dim">
            Current Season Squad
          </div>
          <div className="text-[14px] font-bold mt-0.5">{team || '—'}</div>
        </div>
        <span className={`text-[10px] font-bold px-[9px] py-[3px] rounded-full ${isHome ? 'bg-green/10 text-green' : 'bg-blue/10 text-blue'}`}>
          {players.length} players
        </span>
      </div>

      <div className="px-[18px] pb-[18px]">
        {players.length === 0 ? (
          <div className="text-center py-[22px] text-xs text-muted">
            {team ? 'No current-season players found' : `Select ${isHome ? 'home' : 'away'} team`}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2 max-[520px]:grid-cols-1">
            {visiblePlayers.map((player, index) => {
              const group = posGroup(player.position)
              return (
                <div key={`${player.name}-${index}`} className="flex items-center gap-2 bg-white/[0.025] rounded-[8px] px-2.5 py-2 min-w-0">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-extrabold shrink-0 ${isHome ? 'bg-green/15 text-green' : 'bg-blue/15 text-blue'}`}>
                    {initials(player.name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-semibold truncate">{player.name}</div>
                    <span className={`text-[8px] font-extrabold ${POS_STYLES[group]}`}>{player.position}</span>
                  </div>
                  <button type="button" onClick={() => removePlayer(index)} className="text-muted hover:text-red text-xs px-1">×</button>
                </div>
              )
            })}
          </div>
        )}

        {players.length > 8 && (
          <button type="button" onClick={() => setExpanded(value => !value)} className="w-full mt-2 py-2 text-[11px] font-semibold text-blue hover:text-green transition-colors">
            {expanded ? 'Show less' : `Show all ${players.length} players`}
          </button>
        )}

        <button className="w-full py-[9px] mt-1 bg-transparent border border-dashed border-white/[0.06] rounded-[9px] text-muted text-xs hover:border-green hover:text-green hover:bg-green/10 transition-all" onClick={onAddManual}>
          ＋ Add Player
        </button>
      </div>
    </div>
  )
}
