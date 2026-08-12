from dataclasses import dataclass, field
from typing import List, Dict

RULESET_VERSION = "0.2.0-prototype"

@dataclass
class Patient:
    age: int
    sex: str
    diagnoses: List[str]
    beta_blocker: bool
    ivabradine: bool
    objective: str

@dataclass
class Structural:
    valve_severity: str
    lvef: float
    aorta_mm: float
    aorta_growth_mm_y: float
    hcm_obstructive: bool
    hcm_syncope: bool
    hcm_nsvt: bool
    hcm_family_scd: bool
    arrhythmic_cm: bool
    device: str
    device_upper_rate: int
    icd_therapy_zone: int

@dataclass
class CPET:
    vo2_peak: float
    vo2_pct: float
    rer: float
    vt1_hr: int
    vt2_hr: int
    vt1_load: float
    vt2_load: float
    ve_vco2: float
    sbp_rest: int
    sbp_peak: int
    rhythm: str
    ischemia: bool
    angina: bool
    syncope: bool
    complex_ventricular_arrhythmia: bool
    desaturation: bool
    abnormal_bp_response: bool
    vt1_confidence: str
    vt2_confidence: str

@dataclass
class Decision:
    level: str
    reasons: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    rule_ids: List[str] = field(default_factory=list)

def upgrade(level: str, target: str) -> str:
    rank = {"VERDE":0, "AMARELO":1, "VERMELHO":2}
    return target if rank[target] > rank[level] else level

def safety_engine(patient: Patient, structural: Structural, cpet: CPET) -> Decision:
    level = "VERDE"; reasons=[]; modifiers=[]; rules=[]
    d=set(patient.diagnoses)
    if cpet.syncope:
        level=upgrade(level,"VERMELHO"); reasons.append("Síncope/pré-síncope relacionada ao esforço"); rules.append("SAFE-SYNCOPE-001")
    if cpet.complex_ventricular_arrhythmia:
        level=upgrade(level,"VERMELHO"); reasons.append("Arritmia ventricular complexa/relevante durante o esforço"); rules.append("SAFE-VA-001")
    if cpet.angina and cpet.ischemia:
        level=upgrade(level,"VERMELHO"); reasons.append("Angina associada a evidência de isquemia no esforço"); rules.append("SAFE-ISCHEMIA-002")
    elif cpet.ischemia:
        level=upgrade(level,"AMARELO"); reasons.append("Isquemia induzida pelo esforço: teto de intensidade deve ser definido manualmente"); rules.append("SAFE-ISCHEMIA-001")
    if cpet.abnormal_bp_response:
        level=upgrade(level,"AMARELO"); reasons.append("Resposta pressórica anormal ao esforço"); rules.append("SAFE-BP-001")
    if cpet.desaturation:
        level=upgrade(level,"AMARELO"); reasons.append("Dessaturação relevante durante o esforço"); rules.append("SAFE-SPO2-001")
    if cpet.vt1_confidence != "Alta":
        level=upgrade(level,"AMARELO"); reasons.append("VT1 com confiança abaixo de alta"); rules.append("SAFE-VT1-001")
    if cpet.vt2_confidence == "Baixa":
        level=upgrade(level,"AMARELO"); reasons.append("VT2 com baixa confiança"); rules.append("SAFE-VT2-001")
    if "Valvopatia" in d and structural.valve_severity == "Importante":
        level=upgrade(level,"AMARELO"); reasons.append("Valvopatia importante: prescrição automática não deve depender apenas do CPET"); rules.append("VALVE-SEV-001")
        if cpet.syncope or cpet.abnormal_bp_response:
            level=upgrade(level,"VERMELHO"); reasons.append("Valvopatia importante associada a sintoma/resposta hemodinâmica preocupante"); rules.append("VALVE-SEV-002")
    if "Aortopatia" in d:
        if structural.aorta_mm <= 0:
            level=upgrade(level,"AMARELO"); reasons.append("Aortopatia informada sem diâmetro aórtico: dado estrutural obrigatório ausente"); rules.append("AORTA-DATA-001")
        if structural.aorta_growth_mm_y >= 3.0:
            level=upgrade(level,"AMARELO"); reasons.append("Crescimento aórtico relevante informado; revisar antes de exercício intenso/resistido"); rules.append("AORTA-GROWTH-001")
        modifiers.append("Separar decisão aeróbica da resistida; evitar automatizar esforços máximos/near-max e Valsalva.")
    if "CMH" in d:
        risk_markers = structural.hcm_syncope or structural.hcm_nsvt or structural.hcm_family_scd
        if risk_markers:
            level=upgrade(level,"AMARELO"); reasons.append("CMH com marcador(es) de risco informado(s): exercício vigoroso requer avaliação específica"); rules.append("HCM-RISK-001")
        if structural.hcm_syncope or cpet.complex_ventricular_arrhythmia:
            level=upgrade(level,"VERMELHO"); reasons.append("CMH com síncope/arrítmia ventricular relevante: bloquear automatização"); rules.append("HCM-RISK-002")
    if "Cardiomiopatia dilatada/arrítmica" in d and structural.arrhythmic_cm:
        level=upgrade(level,"AMARELO"); reasons.append("Fenótipo arrítmico: capacidade funcional não deve ser usada isoladamente para liberar alta intensidade"); rules.append("ACM-EX-001")
        if cpet.complex_ventricular_arrhythmia or cpet.syncope:
            level=upgrade(level,"VERMELHO"); reasons.append("Fenótipo arrítmico + evento de alto risco no esforço"); rules.append("ACM-EX-002")
    if "MP/CRT/CDI" in d:
        if structural.device == "CDI" and structural.icd_therapy_zone > 0:
            if cpet.vt2_hr > 0 and structural.icd_therapy_zone - cpet.vt2_hr <= 20:
                level=upgrade(level,"AMARELO"); reasons.append("VT2 aproxima-se da zona de terapia do CDI; revisar programação e teto de exercício"); rules.append("ICD-ZONE-001")
            if cpet.vt2_hr >= structural.icd_therapy_zone:
                level=upgrade(level,"VERMELHO"); reasons.append("VT2 atinge/ultrapassa zona de terapia informada do CDI"); rules.append("ICD-ZONE-002")
        if structural.device in ["MP","CRT-P","CRT-D"] and structural.device_upper_rate > 0 and cpet.vt2_hr >= structural.device_upper_rate:
            level=upgrade(level,"AMARELO"); reasons.append("FC no VT2 atinge/supera limite superior programado informado; avaliar possível limitação do dispositivo"); rules.append("DEVICE-RATE-001")
    if level=="VERDE":
        reasons.append("Sem red flags informadas no formulário"); rules.append("SAFE-GREEN-001")
    return Decision(level,reasons,modifiers,rules)

def disease_engines(patient: Patient, structural: Structural, cpet: CPET) -> List[str]:
    notes=[]; d=set(patient.diagnoses)
    if "DAC" in d: notes.append("DAC: isquemia é o principal limitador; se ausente, os limiares podem ancorar a intensidade, sempre subordinados ao Safety Engine.")
    if "Insuficiência cardíaca" in d: notes.append("IC: separar prognóstico (VO₂/VE-VCO₂ e outros) de prescrição (VT1/VT2, carga, Borg e sintomas).")
    if "Hipertensão" in d: notes.append("HAS: considerar PA basal/curva pressórica; resistido deve enfatizar técnica respiratória e evitar Valsalva quando aplicável.")
    if "Fibrilação atrial" in d: notes.append("FA em CPET: priorizar carga, VT, Borg e sintomas; FC é auxiliar quando o ritmo é irregular.")
    if "Valvopatia" in d: notes.append(f"Valvopatia: gravidade informada = {structural.valve_severity}; dados estruturais prevalecem sobre uma liberação baseada apenas no CPET.")
    if "Aortopatia" in d: notes.append(f"Aortopatia: maior diâmetro informado = {structural.aorta_mm:.0f} mm; avaliar etiologia, crescimento, PA e modalidade resistida separadamente.")
    if "CMH" in d: notes.append("CMH: exercício recreacional leve/moderado e exercício vigoroso devem ser tratados como decisões distintas; marcadores de risco modificam a recomendação.")
    if "Cardiomiopatia dilatada/arrítmica" in d: notes.append("Cardiomiopatia dilatada/arrítmica: função/VO₂ preservados não anulam risco arrítmico.")
    if "MP/CRT/CDI" in d: notes.append("Dispositivo: confrontar resposta cronotrópica com limites programados e, em CDI, zonas de detecção/terapia.")
    return notes or ["Nenhum Disease Engine específico selecionado."]

def prescription_engine(patient: Patient, structural: Structural, cpet: CPET, safety: Decision) -> Dict[str,str]:
    if safety.level=="VERMELHO":
        return {"status":"Bloqueada","aerobico":"Não gerar prescrição automática.","resistido":"Decisão individual após revisão clínica.","monitorizacao":"Revisão médica obrigatória."}
    low_hr=cpet.vt1_hr if cpet.vt1_hr>0 else None; high_hr=None
    if cpet.vt1_hr>0 and cpet.vt2_hr>cpet.vt1_hr and cpet.vt1_confidence=="Alta":
        high_hr=round(cpet.vt1_hr+0.60*(cpet.vt2_hr-cpet.vt1_hr))
    if "Fibrilação atrial" in patient.diagnoses and cpet.rhythm=="Fibrilação atrial":
        load_hi=max(cpet.vt1_load,cpet.vt1_load+0.6*(cpet.vt2_load-cpet.vt1_load))
        monitor=f"Priorizar carga aproximadamente {cpet.vt1_load:.0f}–{load_hi:.0f} W, Borg 11–13/20 e sintomas; FC apenas auxiliar."
    elif low_hr and high_hr:
        monitor=f"Faixa provisória do protótipo para revisão: {low_hr}–{high_hr} bpm + Borg 11–13/20."
    else:
        monitor="Usar Borg, talk test, carga externa e sintomas; dados insuficientes para faixa de FC confiável."
    resist="2–3x/semana apenas se não houver restrição específica; técnica controlada, progressão conservadora, evitar Valsalva/esforço máximo quando indicado."
    if "Aortopatia" in patient.diagnoses: resist="Revisão específica obrigatória do componente resistido; não automatizar cargas altas, esforço máximo/near-max ou Valsalva."
    if "Valvopatia" in patient.diagnoses and structural.valve_severity=="Importante": resist="Não gerar parâmetros resistidos automaticamente até revisão da gravidade/repercussão da valvopatia."
    status="Revisão obrigatória" if safety.level=="AMARELO" else "Sugestão elegível para revisão"
    return {"status":status,"aerobico":"Exercício contínuo leve–moderado, inicialmente 20–30 min, 3–5x/semana; progredir duração antes de intensidade, conforme tolerância e contexto clínico.","resistido":resist,"monitorizacao":monitor}
