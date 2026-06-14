import { useState, useCallback } from 'react'
import Header from './components/Header'
import MatchSetup from './components/MatchSetup'
import LineupPanel from './components/LineupPanel'
import PredictButton from './components/PredictButton'
import ResultsSection from './components/ResultsSection'
import AddPlayerModal from './components/AddPlayerModal'
import Toast from './components/Toast'
import './App.css'

const localDateString = () => {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

export default function App() {
  const [matchDate, setMatchDate]     = useState(localDateString)
  const [homePlayers, setHomePlayers] = useState([])
  const [awayPlayers, setAwayPlayers] = useState([])
  const [homeTeam, setHomeTeam]       = useState('')
  const [awayTeam, setAwayTeam]       = useState('')
  const [results, setResults]         = useState(null)
  const [loading, setLoading]         = useState(false)
  const [modal, setModal]             = useState(null)
  const [toast, setToast]             = useState(null)

  const showToast = useCallback((type, msg) => {
    setToast({ type, msg, id: Date.now() })
  }, [])

  const buildPlayer = useCallback((player, side, team) => {
    return {
      name: player.name,
      team,
      position: player.position || 'MC',
      is_home: side === 'home' ? 1 : 0,
      is_first_eleven: 1,
      age: player.age ?? null,
    }
  }, [])

  const loadTeamPlayers = useCallback(async (side, team, predictionDate) => {
    if (!team) return []
    const params = new URLSearchParams({ prediction_date: predictionDate })
    const res = await fetch(`/api/players/${encodeURIComponent(team)}?${params}`)
    if (!res.ok) throw new Error(res.statusText)
    const data = await res.json()
    return data.players.map(p => buildPlayer(p, side, team))
  }, [buildPlayer])

  const handleTeamChange = useCallback(async (side, team) => {
    if (side === 'home') { setHomeTeam(team); setHomePlayers([]) }
    else                 { setAwayTeam(team); setAwayPlayers([]) }
    if (!team) return
    try {
      const mapped = await loadTeamPlayers(side, team, matchDate)
      if (side === 'home') setHomePlayers(mapped)
      else                 setAwayPlayers(mapped)
    } catch {
      showToast('err', '❌ Failed to load squad')
    }
  }, [loadTeamPlayers, matchDate, showToast])

  const handleDateChange = useCallback(async (dateValue) => {
    setMatchDate(dateValue)
    setResults(null)
    try {
      const [home, away] = await Promise.all([
        homeTeam ? loadTeamPlayers('home', homeTeam, dateValue) : Promise.resolve([]),
        awayTeam ? loadTeamPlayers('away', awayTeam, dateValue) : Promise.resolve([]),
      ])
      setHomePlayers(home)
      setAwayPlayers(away)
    } catch {
      showToast('err', 'Failed to load squads for the selected date')
    }
  }, [awayTeam, homeTeam, loadTeamPlayers, showToast])

  const handlePredict = useCallback(async () => {
    if (!homeTeam || !awayTeam) { showToast('err', '⚠️ Select both teams'); return }
    if (!matchDate) { showToast('err', 'Select the match date'); return }
    const all = [...homePlayers, ...awayPlayers].map(player => ({
      name: player.name,
      team: player.team,
      position: player.position,
      is_home: player.is_home,
      is_first_eleven: player.is_first_eleven,
      age: player.age,
    }))
    setLoading(true)
    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          home_team: homeTeam, away_team: awayTeam,
          prediction_date: matchDate,
          players: all,
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
  }, [homeTeam, awayTeam, matchDate, homePlayers, awayPlayers, showToast])

  return (
    <div className="app-root">
      <Header />
      <main className="main">
        <div className="max-w-[1360px] mx-auto px-7 relative z-[1]">
          <MatchSetup
            homeTeam={homeTeam} awayTeam={awayTeam}
            matchDate={matchDate}
            onHomeTeam={t => handleTeamChange('home', t)}
            onAwayTeam={t => handleTeamChange('away', t)}
            onMatchDate={handleDateChange}
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
