import React from 'react';
import './index.css';

export default function App() {
  return (
    <div className="app-container">
      {/* ── TOP NAV ── */}
      <header className="top-nav">
        <div className="nav-left">
          <div className="logo-main">TALENTSIA.</div>
          <div className="logo-sub">SYSTEM BLUEPRINT V1.0</div>
        </div>
        <div className="nav-center">
          <button className="nav-item active">DASHBOARD</button>
          <button className="nav-item">AGENTS</button>
          <button className="nav-item">MODELS</button>
          <button className="nav-item">COSTS</button>
        </div>
        <div className="nav-right">
          <div className="status-indicator">
            <div className="status-dot"></div>
            STATUS <br/> LIVE PIPELINE
          </div>
          <button className="btn-black">SYSTEM LOGS</button>
        </div>
      </header>

      <main className="dashboard-content">
        
        {/* 01. FULL PIPELINE STATUS */}
        <section>
          <div className="section-title">
            <span>01 — FULL PIPELINE STATUS</span>
            <span style={{ fontSize: '10px', fontWeight: 400 }}>AUTOMATION CYCLE: ACTIVE</span>
          </div>
          <div className="pipeline-layers">
            <PipelineLayer id="01" title="DATA INGESTION" sub="X, REDDIT, RSS" percent="85%" color="green" />
            <PipelineLayer id="02" title="SCORE & RANK" sub="SENTENCE-TRANSFORMERS" percent="60%" color="blue" />
            <PipelineLayer id="03" title="SCRIPT GEN" sub="MISTRAL 7B FT" percent="30%" color="blue" />
            <PipelineLayer id="04" title="VISUAL GEN" sub="FLUX.1 / COGVIDEO" percent="10%" color="blue" />
            <PipelineLayer id="05" title="VOICE SYNTH" sub="XTTS-V2" percent="0%" color="none" />
            <PipelineLayer id="06" title="AVATAR OVERLAY" sub="SADTALKER / MOVIEPY" percent="0%" color="none" />
            <PipelineLayer id="07" title="PUBLISH" sub="IG API / TELEGRAM" percent="0%" color="none" />
          </div>
        </section>

        <div className="grid-2col">
          {/* 02. AUTONOMOUS AGENTS */}
          <section>
            <div className="section-title">
              <div>02 — AUTONOMOUS AGENTS <span style={{marginLeft: 24, fontSize: '10px'}}>FILTER: <strong style={{color: '#000'}}>ALL AGENTS</strong></span></div>
              <span style={{ fontSize: '10px', fontWeight: 400 }}>TOTAL: 6 ACTIVE</span>
            </div>
            <div className="agents-grid">
              
              <div className="agent-card agent-scraper">
                <div className="agent-header">
                  <div className="agent-icon-title">
                    <span className="agent-icon" style={{color: 'var(--accent-yellow)'}}>🔍</span>
                    <span className="agent-title">SCRAPER AGENT</span>
                  </div>
                  <span className="agent-tag idle">IDLE</span>
                </div>
                <div className="agent-desc">Monitoring 12 sources for AI/Tech news.</div>
                <div className="agent-footer">
                  <span>UPTIME: 99.9%</span>
                  <span>LAST: 2m ago</span>
                </div>
              </div>

              <div className="agent-card agent-writer">
                <div className="agent-header">
                  <div className="agent-icon-title">
                    <span className="agent-icon" style={{color: 'var(--accent-blue)'}}>✍️</span>
                    <span className="agent-title">WRITER AGENT</span>
                  </div>
                  <span className="agent-tag writing">WRITING</span>
                </div>
                <div className="agent-desc">Drafting: "The Future of Open Source LLMs"</div>
                <div className="agent-footer">
                  <span>INFERENCE: 1.2s</span>
                  <span>TOKENS: 452</span>
                </div>
              </div>

              <div className="agent-card agent-visual">
                <div className="agent-header">
                  <div className="agent-icon-title">
                    <span className="agent-icon" style={{color: 'var(--accent-purple)'}}>🖼️</span>
                    <span className="agent-title">VISUAL AGENT</span>
                  </div>
                  <span className="agent-tag waiting">WAITING</span>
                </div>
                <div className="agent-desc">Awaiting script from Writer Agent.</div>
                <div className="agent-footer">
                  <span>GPU LOAD: 0%</span>
                  <span>VRAM: 12GB Free</span>
                </div>
              </div>

              <div className="agent-card agent-publisher">
                <div className="agent-header">
                  <div className="agent-icon-title">
                    <span className="agent-icon" style={{color: 'var(--accent-blue)'}}>📤</span>
                    <span className="agent-title">PUBLISHER</span>
                  </div>
                  <span className="agent-tag active">ACTIVE</span>
                </div>
                <div className="agent-desc">Next post scheduled for 18:00 IST.</div>
                <div className="agent-footer">
                  <span>API: IG-Graph</span>
                  <span>SUCCESS: 100%</span>
                </div>
              </div>

            </div>
          </section>

          {/* Right Column: Cost & Model Inference */}
          <div>
            <section>
              <div className="section-title">
                <span>03 — COST ANALYSIS</span>
              </div>
              <div className="cost-card">
                <div className="cost-title">TOTAL MONTHLY BURN</div>
                <div className="cost-amount">
                  ~$145.50
                  <span className="cost-budget">Budget: $200</span>
                </div>
                
                <div className="cost-breakdown">
                  <div className="cost-row">
                    <span>COMPUTE (RunPod/Colab)</span>
                    <strong>$40.00</strong>
                  </div>
                  <div className="cost-row">
                    <span>API COSTS (X/IG)</span>
                    <strong>$105.50</strong>
                  </div>
                  <div className="cost-row free">
                    <span>AI MODELS (Self-hosted)</span>
                    <strong>$0.00</strong>
                  </div>
                </div>
              </div>
            </section>

            <section className="inference-section">
              <div className="section-title">
                <span>04 — MODEL INFERENCE</span>
              </div>
              
              <div className="model-row">
                <div className="model-header">
                  <span>MISTRAL 7B (WRITER)</span>
                  <span className="model-time">1.2s avg</span>
                </div>
                <div className="model-bar-bg"><div className="model-bar-fill" style={{width: '80%'}}></div></div>
              </div>

              <div className="model-row">
                <div className="model-header">
                  <span>FLUX.1 (VISUAL)</span>
                  <span className="model-time">4.5s avg</span>
                </div>
                <div className="model-bar-bg"><div className="model-bar-fill" style={{width: '35%'}}></div></div>
              </div>
            </section>
          </div>
        </div>

        {/* 05. PUBLICATION QUEUE */}
        <section>
          <div className="section-title">
            <span>05 — PUBLICATION QUEUE</span>
            <span style={{ fontSize: '10px', display: 'flex', gap: 12 }}>
              <span style={{color: 'var(--accent-green)'}}>● READY</span>
              <span style={{color: 'var(--accent-blue)'}}>● PROCESSING</span>
            </span>
          </div>
          <div className="queue-grid">
            
            <div className="queue-card">
              <div className="queue-image-placeholder" style={{background: '#DFDFDF'}}>
                <span className="ready-tag">READY</span>
                <div style={{color: '#999', fontSize: 13, textAlign: 'center'}}>CONTENT<br/><span style={{fontSize: 10, fontFamily: 'var(--font-mono)'}}>WAVEFORM</span></div>
              </div>
              <div className="queue-info">
                <div className="queue-title">MISTRAL VS LLAMA 3 COMPARISON</div>
                <div className="queue-meta">Post ID: #REL-9483</div>
                <div className="queue-footer">
                  <span>18:00 IST</span>
                  <span className="time-left">0h 12m left</span>
                </div>
              </div>
            </div>

            <div className="queue-card">
              <div className="queue-image-placeholder rendering">
                <div style={{fontSize: 32, marginBottom: 8}}>🔄</div>
                RENDERING...
              </div>
              <div className="queue-info">
                <div className="queue-title">TOP 5 AI TOOLS OF THE WEEK</div>
                <div className="queue-meta">Post ID: #REL-9484</div>
                <div className="queue-footer">
                  <span>22:00 IST</span>
                  <span className="time-left">...</span>
                </div>
              </div>
            </div>

            <div className="queue-card empty">
              <div style={{fontSize: 24, marginBottom: 8}}>+</div>
              MANUAL ENTRY
            </div>

            <div className="queue-card empty" style={{borderStyle: 'dashed', borderColor: '#E5E5E5'}}>
              AWAITING QUEUE...
            </div>

          </div>
        </section>

        {/* 06. PERFORMANCE ANALYTICS */}
        <section>
          <div className="section-title">
            <div>06 — PERFORMANCE ANALYTICS (LAST 24H) <span style={{marginLeft: 24, fontSize: '10px'}}>FILTER: <strong style={{color: '#000'}}>ALL SYSTEMS</strong></span></div>
            <div style={{display: 'flex', gap: '4px'}}>
              <span style={{fontSize: '10px', marginRight: 8, alignSelf: 'center'}}>RANGE:</span>
              <button style={{padding: '2px 6px', fontSize: '9px', border: '1px solid #ccc', background: '#fff', cursor: 'pointer'}}>1H</button>
              <button style={{padding: '2px 6px', fontSize: '9px', border: '1px solid #ccc', background: '#fff', cursor: 'pointer'}}>6H</button>
              <button style={{padding: '2px 6px', fontSize: '9px', border: 'none', background: '#000', color: '#fff', cursor: 'pointer'}}>24H</button>
            </div>
          </div>
          <div className="analytics-grid">
            
            <div className="chart-card">
              <div className="chart-header">
                <span>AGENT UPTIME (%)</span>
                <strong>99.8% AVG</strong>
              </div>
              <div className="chart-placeholder">
                <svg width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 100 50">
                  <path d="M0,25 L10,20 L20,30 L30,25 L40,35 L50,25 L60,30 L70,20 L80,35 L90,20 L100,25" fill="none" stroke="var(--accent-red)" strokeWidth="2" />
                  <path d="M0,25 L10,20 L20,30 L30,25 L40,35 L50,25 L60,30 L70,20 L80,35 L90,20 L100,25 L100,50 L0,50 Z" fill="rgba(255, 59, 48, 0.1)" />
                </svg>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)'}}>
                <span>24H AGO</span>
                <span>12H AGO</span>
                <span>NOW</span>
              </div>
            </div>

            <div className="chart-card">
              <div className="chart-header">
                <span>INFERENCE LATENCY (AVG)</span>
                <span></span>
              </div>
              <div style={{paddingTop: 16}}>
                <div className="bar-row">
                  <span style={{width: 60}}>MISTRAL 7B</span>
                  <div className="bar-bg"><div className="bar-fg" style={{width: '20%'}}></div></div>
                  <span>1.2S</span>
                </div>
                <div className="bar-row">
                  <span style={{width: 60}}>FLUX.1 DEV</span>
                  <div className="bar-bg"><div className="bar-fg" style={{width: '90%'}}></div></div>
                  <span>4.5S</span>
                </div>
                <div className="bar-row">
                  <span style={{width: 60}}>XTTS-V2</span>
                  <div className="bar-bg"><div className="bar-fg" style={{width: '45%'}}></div></div>
                  <span>2.1S</span>
                </div>
              </div>
            </div>

            <div className="chart-card">
              <div className="chart-header">
                <span>THROUGHPUT (HR)</span>
                <div style={{display: 'flex', gap: 12}}>
                  <span style={{color: 'var(--accent-blue)'}}>● TOKENS</span>
                  <span style={{color: 'var(--accent-purple)'}}>● IMAGES</span>
                </div>
              </div>
              <div className="chart-placeholder">
                <svg width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 100 50">
                  <path d="M0,45 L20,25 L40,40 L60,20 L80,35 L100,25" fill="none" stroke="var(--accent-blue)" strokeWidth="2" strokeDasharray="3,3" />
                  <path d="M0,48 L20,45 L40,42 L60,45 L80,41 L100,43" fill="none" stroke="var(--accent-purple)" strokeWidth="2" />
                </svg>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)'}}>
                <span>TOTAL (24H)<br/><strong style={{color: '#000', fontSize: '10px'}}>482K TOKENS / 142 MEDIA</strong></span>
                <span style={{alignSelf: 'flex-end'}}>LIVE UPDATE</span>
              </div>
            </div>

          </div>
        </section>

      </main>

      {/* ── FOOTER ── */}
      <footer className="footer">
        <div>© TALENTSIA CONTENT PIPELINE &nbsp;&nbsp; 100% OPEN SOURCE &nbsp;&nbsp; STACK: PYTHON / LLM / DOCKER</div>
        <div style={{display: 'flex', gap: 16, alignItems: 'center'}}>
          <span>🐙</span>
          <button className="footer-btn">FULL REPOSITORY LAYOUT</button>
        </div>
      </footer>
    </div>
  );
}

function PipelineLayer({ id, title, sub, percent, color }) {
  return (
    <div className="layer-card">
      <div className="layer-id">LAYER {id}</div>
      <div className="layer-title">{title}</div>
      <div className="progress-bar-container">
        <div className={`progress-bar-fill ${color}`} style={{ width: percent }}></div>
      </div>
      <div className="layer-sub">{sub}</div>
    </div>
  );
}
