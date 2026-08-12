import streamlit as st
from clinical_engine_v0_2 import (Patient, Structural, CPET, RULESET_VERSION, safety_engine, disease_engines, prescription_engine)

st.set_page_config(page_title="CPET Exercise Prescription MVP 0.3 UI", layout="wide")

st.title('CPET Exercise Prescription — MVP 0.3 UI')
st.caption(f'Protótipo técnico • ruleset {RULESET_VERSION} • não validado para uso clínico autônomo')

with st.sidebar:
    st.header('1. Paciente')
    age=st.number_input('Idade',18,100,60); sex=st.selectbox('Sexo',['Masculino','Feminino','Outro/Não informado'])
    diagnoses=st.multiselect(
        'Diagnósticos cardiovasculares',
        ['DAC','Insuficiência cardíaca','Hipertensão','Fibrilação atrial','Valvopatia','Aortopatia','CMH','Cardiomiopatia dilatada/arrítmica','MP/CRT/CDI'],
        format_func=lambda x: {
            'DAC':'Doença arterial coronariana (DAC)',
            'Insuficiência cardíaca':'Insuficiência cardíaca',
            'Hipertensão':'Hipertensão arterial',
            'Fibrilação atrial':'Fibrilação atrial',
            'Valvopatia':'Valvopatia',
            'Aortopatia':'Aortopatia',
            'CMH':'Cardiomiopatia hipertrófica (CMH)',
            'Cardiomiopatia dilatada/arrítmica':'Cardiomiopatia dilatada/arrítmica',
            'MP/CRT/CDI':'Marcapasso / CRT / CDI'
        }[x]
    )
    if 'DAC' in diagnoses:
        st.markdown('**Detalhes da DAC**')
        st.checkbox('IAM prévio', key='dac_iam')
        st.checkbox('Angioplastia / stent prévio', key='dac_pci')
        st.checkbox('Cirurgia de revascularização prévia', key='dac_cabg')
        st.selectbox('Situação clínica da DAC',['Estável / assintomático','Angina estável','Sintomas em investigação'], key='dac_status')
    beta=st.checkbox('Betabloqueador'); iva=st.checkbox('Ivabradina')
    objective=st.selectbox('Objetivo principal',['Saúde cardiovascular','Reabilitação','Condicionamento','Controle pressórico','Retorno ao exercício'])

st.subheader('2. Dados específicos dos diagnósticos')

# Defaults keep the clinical engine compatible when a module is not active.
valve_severity='Não informada'; lvef=60.0; aorta_mm=0.0; aorta_growth=0.0
hcm_obstructive=False; hcm_syncope=False; hcm_nsvt=False; hcm_family_scd=False
arrhythmic_cm=False; device='Nenhum'; device_upper=0; icd_zone=0

if not any(d in diagnoses for d in ['Insuficiência cardíaca','Valvopatia','Aortopatia','CMH','Cardiomiopatia dilatada/arrítmica','MP/CRT/CDI']):
    st.caption('Nenhum dado estrutural adicional é necessário para os diagnósticos selecionados nesta versão.')

if 'Insuficiência cardíaca' in diagnoses or 'Valvopatia' in diagnoses or 'CMH' in diagnoses or 'Cardiomiopatia dilatada/arrítmica' in diagnoses:
    lvef=st.number_input('FEVE (%)',0.0,80.0,60.0,step=1.0)

if 'Valvopatia' in diagnoses:
    st.markdown('**Valvopatia**')
    valve_severity=st.selectbox('Gravidade da valvopatia',['Não informada','Leve','Moderada','Importante'])

if 'Aortopatia' in diagnoses:
    st.markdown('**Aortopatia**')
    aorta_mm=st.number_input('Maior diâmetro aórtico (mm)',0.0,80.0,0.0,step=1.0)
    aorta_growth=st.number_input('Crescimento aórtico (mm/ano)',0.0,20.0,0.0,step=0.5)

if 'CMH' in diagnoses:
    st.markdown('**Cardiomiopatia hipertrófica**')
    hcm_obstructive=st.checkbox('CMH obstrutiva')
    hcm_syncope=st.checkbox('Síncope suspeita/arrítmica')
    hcm_nsvt=st.checkbox('TVNS documentada')
    hcm_family_scd=st.checkbox('História familiar de morte súbita')

if 'Cardiomiopatia dilatada/arrítmica' in diagnoses:
    st.markdown('**Cardiomiopatia dilatada/arrítmica**')
    arrhythmic_cm=st.checkbox('Fenótipo de cardiomiopatia arrítmica')

if 'MP/CRT/CDI' in diagnoses:
    st.markdown('**Dispositivo cardíaco**')
    device=st.selectbox('Dispositivo',['MP','CRT-P','CDI','CRT-D'])
    device_upper=st.number_input('Upper tracking/max sensor rate (bpm)',0,220,0)
    if device in ['CDI','CRT-D']:
        icd_zone=st.number_input('Zona de terapia do CDI (bpm)',0,250,0)

st.subheader('3. Dados do CPET')
col1,col2,col3=st.columns(3)
with col1:
    vo2_peak=st.number_input('VO₂ pico (mL/kg/min)',0.0,80.0,24.0,step=0.1); vo2_pct=st.number_input('VO₂ previsto (%)',0.0,200.0,85.0,step=1.0); rer=st.number_input('RER pico',0.7,2.0,1.10,step=0.01); ve_vco2=st.number_input('VE/VCO₂ slope',10.0,80.0,30.0,step=0.1)
with col2:
    vt1_hr=st.number_input('FC no VT1',0,220,105); vt2_hr=st.number_input('FC no VT2/RCP',0,220,135); vt1_load=st.number_input('Carga no VT1 (W)',0.0,500.0,80.0,step=5.0); vt2_load=st.number_input('Carga no VT2 (W)',0.0,500.0,130.0,step=5.0)
with col3:
    sbp_rest=st.number_input('PAS repouso',60,260,130); sbp_peak=st.number_input('PAS pico',80,320,185); rhythm=st.selectbox('Ritmo durante CPET',['Ritmo sinusal','Fibrilação atrial','Estimulado por dispositivo','Outro']); vt1_conf=st.selectbox('Confiança VT1',['Alta','Intermediária','Baixa']); vt2_conf=st.selectbox('Confiança VT2',['Alta','Intermediária','Baixa'])

st.subheader('4. Achados de segurança')
c1,c2,c3=st.columns(3)
with c1:
    ischemia=st.checkbox('Isquemia no esforço')
    angina=st.checkbox('Angina no esforço')
    if 'DAC' in diagnoses and (ischemia or angina):
        st.number_input('FC no início da isquemia/angina (bpm)',0,220,0,key='ischemia_hr')
        st.number_input('Carga no início da isquemia/angina (W)',0.0,500.0,0.0,step=5.0,key='ischemia_load')
with c2: syncope=st.checkbox('Síncope/pré-síncope no CPET'); complex_va=st.checkbox('Arritmia ventricular complexa')
with c3: desat=st.checkbox('Dessaturação relevante'); abnormal_bp=st.checkbox('Resposta pressórica anormal')

patient=Patient(age,sex,diagnoses,beta,iva,objective)
structural=Structural(valve_severity,lvef,aorta_mm,aorta_growth,hcm_obstructive,hcm_syncope,hcm_nsvt,hcm_family_scd,arrhythmic_cm,device,device_upper,icd_zone)
cpet=CPET(vo2_peak,vo2_pct,rer,int(vt1_hr),int(vt2_hr),vt1_load,vt2_load,ve_vco2,int(sbp_rest),int(sbp_peak),rhythm,ischemia,angina,syncope,complex_va,desat,abnormal_bp,vt1_conf,vt2_conf)

if st.button('Analisar caso',type='primary'):
    safety=safety_engine(patient,structural,cpet); disease_notes=disease_engines(patient,structural,cpet); rx=prescription_engine(patient,structural,cpet,safety)
    st.subheader('5. Resultado médico')
    {'VERDE':st.success,'AMARELO':st.warning,'VERMELHO':st.error}[safety.level](f'Safety Engine: {safety.level}')
    st.write('**Motivos / alertas**'); [st.write(f'- {r}') for r in safety.reasons]
    if safety.modifiers:
        st.write('**Modificadores**'); [st.write(f'- {m}') for m in safety.modifiers]
    st.write('**Disease Engines**'); [st.write(f'- {n}') for n in disease_notes]
    st.write('**Prescrição sugerida**'); st.write(f"**Status:** {rx['status']}"); st.write(f"**Aeróbico:** {rx['aerobico']}"); st.write(f"**Monitorização/intensidade:** {rx['monitorizacao']}"); st.write(f"**Resistido:** {rx['resistido']}")
    st.write('**Trilha de auditoria**'); st.code('Ruleset: '+RULESET_VERSION+'\n'+'\n'.join(safety.rule_ids))
    st.info('Os valores numéricos desta versão continuam sendo heurísticas de prototipação. Regras clínicas numéricas só devem migrar para status validado após vínculo a fonte primária e revisão formal.')
    st.subheader('6. Orientação ao paciente — rascunho')
    if safety.level=='VERMELHO': st.write('Não gerar orientação automática. Caso requer definição médica individual antes da atividade física.')
    else:
        st.write(f"**Atividade aeróbica:** {rx['aerobico']}"); st.write(f"**Como controlar a intensidade:** {rx['monitorizacao']}"); st.write('**Sinais para interromper e procurar avaliação:** dor/pressão torácica, tontura importante, sensação de desmaio, falta de ar muito diferente do habitual ou palpitações persistentes associadas a mal-estar.')

st.divider(); st.caption('MVP 0.3 UI — inclui os nove Disease Engines em modo conservador, regras versionadas e trilha de auditoria. Próxima etapa: testes automatizados e matriz de validação clínica.')
