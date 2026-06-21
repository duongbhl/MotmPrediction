import { useEffect, useRef } from 'react'
import {
  Chart as ChartJS, RadialLinearScale, PointElement,
  LineElement, Filler, Tooltip, Legend,
} from 'chart.js'
import { Radar } from 'react-chartjs-2'
import { posGroup, initials } from '../utils/player'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const POS_STYLES = {
  GK:  'bg-gold/10 text-gold',
  DEF: 'bg-blue/10 text-blue',
  MID: 'bg-green/10 text-green',
  FWD: 'bg-red/10 text-red',
}

const num = value => Number.isFinite(Number(value)) ? Number(value) : 0
const fixed = (value, digits = 1) => num(value).toFixed(digits)

function DonutScore({ score }) {
  const pct    = Math.min(99, Math.round(score))
  const circ   = 283
  const offset = circ - (circ * pct / 100)
  const fillRef = useRef(null)
  const numRef  = useRef(null)

  useEffect(() => {
    if (!fillRef.current) return
    fillRef.current.style.transition = 'none'
    fillRef.current.style.strokeDashoffset = circ
    const raf = requestAnimationFrame(() => {
      fillRef.current.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(.4,0,.2,1)'
      fillRef.current.style.strokeDashoffset = offset
    })
    return () => cancelAnimationFrame(raf)
  }, [score, offset])

  useEffect(() => {
    if (!numRef.current) return
    let start = null
    const duration = 1300
    const tick = (ts) => {
      if (!start) start = ts
      const p = Math.min(1, (ts - start) / duration)
      const e = 1 - Math.pow(1 - p, 3)
      if (numRef.current) numRef.current.textContent = Math.round(pct * e)
      if (p < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [pct])

  return (
    <div className="flex flex-col items-center gap-1.5 shrink-0">
      <div className="relative w-[108px] h-[108px]">
        <svg width="108" height="108" viewBox="0 0 108 108" className="rotate-[-90deg]">
          <circle cx="54" cy="54" r="45"
            fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
          <circle
            ref={fillRef}
            cx="54" cy="54" r="45"
            fill="none" stroke="#00E87A" strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={circ}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[26px] font-black text-green leading-none" ref={numRef}>0</span>
          <span className="text-[9px] font-bold uppercase tracking-[1.4px] text-muted mt-0.5">Chance</span>
        </div>
      </div>
      <span className="text-[9px] font-bold uppercase tracking-[1.2px] text-muted">Squad-relative chance</span>
    </div>
  )
}

function MotmHero({ motm }) {
  const pg = posGroup(motm.position)
  const s  = motm.recent_form || {}
  const STRIP = [
    { l: 'Avg Rating',     v: s.rating == null ? 'N/A' : fixed(s.rating), gold: true },
    { l: 'Avg Goals',      v: fixed(s.goals) },
    { l: 'Avg Assists',    v: fixed(s.assists) },
    { l: 'Avg Key Passes', v: fixed(s.key_passes) },
    { l: 'Avg Shots',      v: fixed(s.shots) },
    { l: 'Avg Tackles',    v: fixed(s.tackles) },
  ]

  return (
    <div className="bg-gradient-to-br from-[rgba(0,232,122,0.07)] to-[rgba(0,184,255,0.04)] border border-green/[0.18] rounded-[16px] p-[22px] mb-5 [animation:fadeUp_0.5s_ease_forwards]">
      {/* Top row */}
      <div className="flex flex-wrap gap-5 items-center">
        {/* Trophy + badge */}
        <div className="flex flex-col items-center gap-1.5 shrink-0">
          <span className="text-[48px] [animation:trophyBounce_0.7s_cubic-bezier(0.34,1.56,0.64,1)_forwards]">🏆</span>
          <span className="text-[9px] font-extrabold uppercase tracking-[2px] text-gold bg-gold/[0.12] border border-gold/[0.18] px-2.5 py-[3px] rounded-full">Man of the Match</span>
        </div>

        {/* Name + meta */}
        <div className="flex-1 min-w-[160px]">
          <div className="text-[11px] font-bold tracking-[2.4px] text-muted uppercase mb-1 [animation:nameSlide_0.5s_ease_forwards]">{motm.team.toUpperCase()}</div>
          <div className="text-[30px] font-black leading-tight [animation:nameSlide_0.5s_ease_0.05s_forwards]">{motm.name}</div>
          <div className="flex items-center gap-2.5 mt-2">
            <span className={`text-[9px] font-extrabold px-[7px] py-[3px] rounded-[5px] tracking-[0.6px] ${POS_STYLES[pg]}`}>{pg}</span>
            <span className="text-xs text-muted">Form from previous 5 matches</span>
          </div>
        </div>

        <DonutScore score={motm.score} />
      </div>

      {/* Stat strip */}
      <div className="grid grid-cols-6 gap-[10px] mt-[18px] pt-[18px] border-t border-white/[0.06] max-[600px]:grid-cols-3">
        {STRIP.map((item, i) => (
          <div
            key={item.l}
            className="flex flex-col items-center gap-1 bg-white/[0.025] rounded-[8px] py-[10px] [animation:valPop_0.4s_ease_forwards]"
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <div className={`text-[20px] font-extrabold leading-none ${item.gold ? 'text-gold' : 'text-text'}`}>{item.v}</div>
            <div className="text-[9px] font-bold uppercase tracking-[1px] text-muted">{item.l}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FeatureDetails({ motm }) {
  const s = motm.recent_form || {}
  const percent = value => value == null ? 'N/A' : `${fixed(num(value) * 100)}%`
  const accuracy = value => value == null ? 'N/A' : `${fixed(value)}%`
  const fields = [
    ['Avg minutes', s.minutes == null ? 'N/A' : fixed(s.minutes)],
    ['Start rate', percent(s.start_rate)],
    ['Shots on target', s.shots_on_target == null ? 'N/A' : fixed(s.shots_on_target)],
    ['Pass accuracy', accuracy(s.pass_accuracy)],
    ['Interceptions', s.interceptions == null ? 'N/A' : fixed(s.interceptions)],
    ['Clearances', s.clearances == null ? 'N/A' : fixed(s.clearances)],
    ['Aerial won', s.aerial_won == null ? 'N/A' : fixed(s.aerial_won)],
    ['Dribbles won', s.dribbles_won == null ? 'N/A' : fixed(s.dribbles_won)],
    ['MOTM rate (10)', percent(s.motm_rate)],
  ]

  return (
    <div className="bg-card border border-white/[0.06] rounded-[14px] p-[18px] mb-5">
      <div className="text-[11px] font-bold tracking-[1.8px] uppercase text-dim mb-3">
        All historical model indicators
      </div>
      <div className="grid grid-cols-3 gap-2.5 max-[700px]:grid-cols-2">
        {fields.map(([label, value]) => (
          <div key={label} className="bg-white/[0.025] rounded-[8px] px-3 py-2.5">
            <div className="text-[14px] font-bold text-text">{value}</div>
            <div className="text-[9px] uppercase tracking-[1px] text-muted mt-1">{label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Contenders({ contenders, topScore }) {
  const denom = Math.max(num(topScore), 0.0001)
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-[12px] mb-5">
      {contenders.slice(0, 5).map((p, i) => (
        <div
          key={p.name}
          className="bg-card border border-white/[0.06] hover:border-white/[0.12] rounded-[12px] p-[14px] flex flex-col gap-[10px] transition-colors [animation:fadeUp_0.4s_ease_forwards]"
          style={{ animationDelay: `${i * 0.08}s` }}
        >
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-black text-muted w-6">#{i + 2}</span>
            <div className="w-[30px] h-[30px] rounded-full bg-gradient-to-br from-blue to-purple flex items-center justify-center text-[11px] font-extrabold shrink-0">
              {initials(p.name)}
            </div>
          </div>
          <div>
            <div className="text-[12px] font-semibold leading-tight">{p.name}</div>
            <div className="text-[10px] text-muted mt-0.5">{p.team}</div>
          </div>
          <div>
            <div className="h-[4px] bg-white/[0.05] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue to-purple rounded-full transition-all duration-1000"
                style={{ width: `${((num(p.score) / denom) * 100).toFixed(0)}%` }}
              />
            </div>
            <div className="text-[11px] font-bold text-blue mt-1.5">{fixed(p.score)}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

function PerformanceRadar({ motm }) {
  const s = motm.recent_form || {}
  const data = {
    labels: ['Rating','Goals','Assists','Key Passes','Shots','Tackles'],
    datasets: [{
      label: motm.name,
      data: [
        (num(s.rating) / 10) * 100,
        (Math.min(num(s.goals), 4)           / 4) * 100,
        (Math.min(num(s.assists), 3)         / 3) * 100,
        (Math.min(num(s.key_passes), 8)      / 8) * 100,
        (Math.min(num(s.shots), 6)           / 6) * 100,
        (Math.min(num(s.tackles), 7)         / 7) * 100,
      ],
      backgroundColor: 'rgba(0,232,122,0.10)',
      borderColor:     'rgba(0,232,122,0.85)',
      borderWidth: 2,
      pointBackgroundColor: '#00E87A',
      pointBorderColor:     '#00E87A',
      pointRadius: 4, pointHoverRadius: 6,
    }],
  }
  const options = {
    responsive: true,
    animation: { duration: 1200, easing: 'easeOutQuart' },
    plugins: { legend: { labels: { color: '#A8B8CC', font: { size: 11 } } } },
    scales: {
      r: {
        min: 0, max: 100,
        ticks: { display: false, stepSize: 25 },
        grid:        { color: 'rgba(255,255,255,0.06)' },
        angleLines:  { color: 'rgba(255,255,255,0.07)' },
        pointLabels: { color: '#4E5E72', font: { size: 10 } },
      },
    },
  }
  return <Radar data={data} options={options} />
}

function Rankings({ allPlayers, topScore }) {
  const medals = ['🥇','🥈','🥉']
  const denom = Math.max(num(topScore), 0.0001)
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-white/[0.06]">
            {['#','Player','Team','Pos','Recent rating','Chance','Bar'].map(h => (
              <th key={h} className="text-[9px] font-extrabold uppercase tracking-[1.6px] text-muted pb-2 text-left last:min-w-[90px]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {allPlayers.map((p, i) => {
            const pg = posGroup(p.position)
            return (
              <tr key={p.name} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                <td className={`py-2.5 pr-2 font-extrabold text-sm ${i < 3 ? 'text-gold' : 'text-muted'}`}>{medals[i] ?? i + 1}</td>
                <td className="py-2.5 pr-3 font-semibold">{p.name}</td>
                <td className="py-2.5 pr-3 text-[11px] text-dim">{p.team}</td>
                <td className="py-2.5 pr-3">
                  <span className={`text-[8px] font-extrabold px-[6px] py-[2px] rounded-[4px] tracking-[0.5px] ${POS_STYLES[pg]}`}>{pg}</span>
                </td>
                <td className="py-2.5 pr-3 text-gold font-bold">{p.recent_form?.rating == null ? 'N/A' : fixed(p.recent_form.rating)}</td>
                <td className="py-2.5 pr-3 text-green font-bold">{fixed(p.score)}</td>
                <td className="py-2.5">
                  <div className="h-[5px] bg-white/[0.05] rounded-full overflow-hidden min-w-[70px]">
                    <div
                      className="h-full bg-gradient-to-r from-green to-[#00B8FF] rounded-full"
                      style={{ width: `${((num(p.score) / denom) * 100).toFixed(0)}%` }}
                    />
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function ResultsSection({ data }) {
  const rankedPlayers = data.all_players || [data.motm, ...(data.top_contenders || [])]

  return (
    <div id="results" className="mt-6 [animation:fadeUp_0.5s_ease_forwards]">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="text-[13px] font-extrabold tracking-[2px] uppercase text-dim">🏆 Man of the Match Prediction</div>
        <div className="text-[11px] text-muted">History before {data.match_info?.prediction_date}</div>
      </div>
      <MotmHero motm={data.motm} topScore={data.top_score} />
      <FeatureDetails motm={data.motm} />

      {data.top_contenders?.length > 0 && (
        <>
          <div className="text-[13px] font-extrabold tracking-[2px] uppercase text-dim mb-4">🥇 Top Contenders</div>
          <Contenders contenders={data.top_contenders} topScore={data.top_score} />
        </>
      )}

      <div className="grid grid-cols-2 gap-[18px] max-[900px]:grid-cols-1">
        {/* Radar card */}
        <div className="bg-card border border-white/[0.06] hover:border-white/[0.12] rounded-[14px] transition-colors">
          <div className="flex items-center gap-2.5 px-[22px] pt-[18px] mb-[18px]">
            <div className="w-[30px] h-[30px] rounded-[8px] bg-gold/10 flex items-center justify-center text-[15px]">📊</div>
            <span className="text-[11px] font-bold tracking-[1.8px] uppercase text-dim">Recent Form — Previous 5 Matches</span>
          </div>
          <div className="px-[22px] pb-[22px]">
            <PerformanceRadar motm={data.motm} />
          </div>
        </div>

        {/* Rankings card */}
        <div className="bg-card border border-white/[0.06] hover:border-white/[0.12] rounded-[14px] transition-colors">
          <div className="flex items-center gap-2.5 px-[22px] pt-[18px] mb-[18px]">
            <div className="w-[30px] h-[30px] rounded-[8px] bg-blue/10 flex items-center justify-center text-[15px]">🏅</div>
            <span className="text-[11px] font-bold tracking-[1.8px] uppercase text-dim">Full Player Rankings</span>
          </div>
          <div className="px-[22px] pb-[22px]">
            <Rankings allPlayers={rankedPlayers} topScore={data.top_score} />
          </div>
        </div>
      </div>
    </div>
  )
}

