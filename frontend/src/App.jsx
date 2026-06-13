import { useState, useCallback } from 'react'
import Header from './components/Header'
import MatchSetup from './components/MatchSetup'
import LineupPanel from './components/LineupPanel'
import PredictButton from './components/PredictButton'
import ResultsSection from './components/ResultsSection'
import AddPlayerModal from './components/AddPlayerModal'
import Toast from './components/Toast'
import './App.css'

export default function App() {
  const [homePlayers, setHomePlayers] = useState([])
  const [awayPlayers, setAwayPlayers] = useState([])
  const [homeTeam, setHomeTeam]       = useState('')
  const [awayTeam, setAwayTeam]       = useState('')
  const [homeScore, setHomeScore]     = useState(0)
  const [awayScore, setAwayScore]     = useState(0)
  const [results, setResults]         = useState(null)
  const [loading, setLoading]         = useState(false)
  const [modal, setModal]             = useState(null)
  const [toast, setToast]             = useState(null)

  const showToast = useCallback((type, msg) => {
    setToast({ type, msg, id: Date.now() })
  }, [])

  const buildPlayer = useCallback((player, side, team) => {
    const stats = player.default_stats || {}
    const passesCompleted = Number(stats.passes_completed ?? 30)
    const passesTotal = Number(stats.passes_total ?? Math.max(passesCompleted, 40))

    return {
      name: player.name,
      team,
      position: player.position || 'MC',
      is_home: side === 'home' ? 1 : 0,
      is_first_eleven: 1,
      age: stats.age ?? null,
      minutes_played: Number(stats.minutes_played ?? 90),
      rating: stats.rating ?? null,
      goals: Number(stats.goals ?? 0),
      assists: Number(stats.assists ?? 0),
      shots_total: Number(stats.shots_total ?? 0),
      shots_on_target: Number(stats.shots_on_target ?? 0),
      key_passes: Number(stats.key_passes ?? 0),
      passes_completed: passesCompleted,
      passes_total: passesTotal,
      pass_accuracy: stats.pass_accuracy ?? null,
      tackles: Number(stats.tackles ?? 0),
      interceptions: Number(stats.interceptions ?? 0),
      clearances: Number(stats.clearances ?? 0),
      aerial_won: Number(stats.aerial_won ?? 0),
      dribbles_won: Number(stats.dribbles_won ?? 0),
      fouls_committed: Number(stats.fouls_committed ?? 0),
    }
  }, [])

  const handleTeamChange = useCallback(async (side, team) => {
    if (side === 'home') { setHomeTeam(team); setHomePlayers([]) }
    else                 { setAwayTeam(team); setAwayPlayers([]) }
    if (!team) return
    try {
      const res  = await fetch(`/api/players/${encodeURIComponent(team)}`)
      const data = await res.json()
      const mapped = data.players.slice(0, 18).map(p => buildPlayer(p, side, team))
      if (side === 'home') setHomePlayers(mapped)
      else                 setAwayPlayers(mapped)
    } catch {
      showToast('err', '❌ Failed to load squad')
    }
  }, [buildPlayer, showToast])

  const handlePredict = useCallback(async () => {
    if (!homeTeam || !awayTeam) { showToast('err', '⚠️ Select both teams'); return }
    const all = [...homePlayers, ...awayPlayers]
    if (!all.length) { showToast('err', '⚠️ Add players first'); return }
    setLoading(true)
    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          home_team: homeTeam, away_team: awayTeam,
          home_score: homeScore, away_score: awayScore, players: all,
        }),
      })
      if (!res.ok) throw new Error(res.statusText)
      const data = await res.json()
      setResults(data)
      showToast('ok', `🏆 ${data.motm.name} — Man of the Match!`)
      setTimeout(() => document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300)
    } catch {
      showToast('err', '❌ Could not reach prediction API')
    } finally {
      setLoading(false)
    }
  }, [homeTeam, awayTeam, homeScore, awayScore, homePlayers, awayPlayers, showToast])

  return (
    <div className="app-root">
      <Header />
      <main className="main">
        <div className="max-w-[1360px] mx-auto px-7 relative z-[1]">
          <MatchSetup
            homeTeam={homeTeam} awayTeam={awayTeam}
            homeScore={homeScore} awayScore={awayScore}
            onHomeTeam={t => handleTeamChange('home', t)}
            onAwayTeam={t => handleTeamChange('away', t)}
            onHomeScore={setHomeScore}
            onAwayScore={setAwayScore}
          />
          <div className="grid grid-cols-2 gap-[18px] mb-5 max-[700px]:grid-cols-1">
            <LineupPanel
              side="home" team={homeTeam}
              players={homePlayers} setPlayers={setHomePlayers}
              onAddManual={() => setModal('home')}
            />
            <LineupPanel
              side="away" team={awayTeam}
              players={awayPlayers} setPlayers={setAwayPlayers}
              onAddManual={() => setModal('away')}
            />
          </div>
          <PredictButton loading={loading} onClick={handlePredict} />
          {results && <ResultsSection data={results} />}
        </div>
      </main>
      {modal && (
        <AddPlayerModal
          side={modal}
          team={modal === 'home' ? homeTeam : awayTeam}
          onClose={() => setModal(null)}
          onSave={p => {
            if (modal === 'home') setHomePlayers(prev => [...prev, p])
            else                  setAwayPlayers(prev => [...prev, p])
            setModal(null)
            showToast('ok', `✅ ${p.name} added`)
          }}
        />
      )}
      {toast && <Toast key={toast.id} type={toast.type} msg={toast.msg} />}
    </div>
  )
}
