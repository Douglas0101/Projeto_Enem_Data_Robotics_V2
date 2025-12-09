Apl# **Plano Diretor de Engenharia de Cibersegurança e Escalabilidade**

Projeto: ENEM Data Robotics V2  
Versão: 1.0  
Status: Arquitetura de Referência

## **1\. Visão Estratégica: Security by Design & Scale**

Este documento define as diretrizes de engenharia para estabelecer a segurança como uma **camada transversal de infraestrutura** no projeto ENEM Data Robotics. O objetivo é assegurar que o crescimento do volume de dados (1998-2024+) e da concorrência de usuários não comprometa a confidencialidade, integridade ou disponibilidade, alinhando-se à arquitetura de referência existente.

### **1.1 Princípios Fundamentais**

1. **Zero Trust Architecture (ZTA):** Validação contínua de autenticação e autorização para cada requisição entre agentes, API e banco de dados.  
2. **Imutabilidade Auditável:** Preservação estrita dos dados brutos (Raw) e logs de segurança; alterações geram novos artefatos versionados.  
3. **Defesa em Profundidade:** Múltiplas barreiras de proteção (WAF, AuthN/AuthZ, Data Masking, Hardening de DB).

## **2\. Arquitetura de Identidade e Acesso (IAM) Escalável**

A arquitetura atual utiliza JWT com Argon2id para autenticação stateless. Para suportar escalabilidade e federação, o plano evolutivo inclui:

### **2.1 Autenticação e Gestão de Sessão**

* **Identity Provider (IdP) Centralizado:** Adoção de soluções como Keycloak ou Auth0 para desacoplar a lógica de autenticação da API (auth\_router.py), habilitando SSO (Single Sign-On) e MFA (Múltiplo Fator).  
* **Hashing Robusto:** Manutenção da configuração industrial do **Argon2id** com memory\_cost=65536, time\_cost=2 e parallelism=2 para resistência a ataques de hardware dedicado (GPU/ASIC).

### **2.2 Controle de Acesso (RBAC/ABAC)**

Expansão do modelo de permissões:

* **Roles:** DATA\_ENGINEER, DATA\_SCIENTIST, AUDITOR, VIEWER.  
* **Escopo:** Restrição granular por camada de dados (read:gold, write:silver, admin:raw).

## **3\. Engenharia de Proteção de Dados (Data Privacy Engineering)**

Foco na conformidade com a LGPD e proteção de PII (Personal Identifiable Information).

### **3.1 Mascaramento Dinâmico (Dynamic Data Masking \- DDM)**

Refinamento da engine de segurança (SecurityEngine) para atuar como interceptador obrigatório:

* **Aplicação:** O método apply\_dynamic\_masking deve ser invocado em todos os endpoints de saída de dados.  
* **Regras:**  
  * **CPF/Inscrição:** Mascaramento parcial (ex: 12\*\*\*78) para usuários sem privilégio administrativo.  
  * **Dados Sensíveis:** Anonimização em tempo de consulta para perfis de analistas.

### **3.2 Criptografia e Integridade**

* **Trânsito:** TLS 1.3 mandatório para comunicações internas e externas.  
* **Integridade de Exportação:** Implementação de verificação de assinatura digital (hash SHA-256) para garantir o não-repúdio de arquivos exportados, conforme stub verify\_export\_signature.

## **4\. Segurança de Aplicação (AppSec) e Pipeline**

Integração com o Orquestrador de Qualidade Nativa para automação de segurança.

### **4.1 Pipeline DevSecOps**

* **SAST/SCA:** Varredura automática de vulnerabilidades em código (ex: injeção SQL, segredos hardcoded) e dependências (poetry.lock).  
* **Gestão de Segredos:** Uso de Cofres Digitais (Vault) para injetar GOOGLE\_API\_KEY e chaves de criptografia em tempo de execução, eliminando-as do código fonte.

### **4.2 Hardening da API**

* **Rate Limiting:** Proteção contra força bruta e DDoS na camada de API (api/limiter.py).  
* **Validação de Input:** Uso estrito de schemas Pydantic para rejeitar payloads maliciosos.

## **5\. Infraestrutura e Escalabilidade Segura**

### **5.1 Isolamento de Recursos (DuckDB)**

Prevenção de exaustão de recursos (DoS) por consultas analíticas pesadas:

* **Modo Leitura:** A API deve instanciar o agente de banco de dados estritamente como read\_only=True.  
* **Cotas de Recursos:** Aplicação de PRAGMAs para limitar memória (memory\_limit) e threads, configurados via variáveis de ambiente para adaptação ao hardware hospedeiro.

### **5.2 Auditoria Centralizada**

* **Logs Estruturados:** Padronização de logs em JSON para ingestão em sistemas SIEM/ELK.  
* **Rastreabilidade:** Registro obrigatório de *quem*, *quando* e *o que* foi acessado, integrando logs de aplicação (infra/logging.py) com logs de auditoria de dados.

## **6\. Roadmap de Implementação**

| Fase | Prioridade | Ação Chave | Componentes Afetados |
| :---- | :---- | :---- | :---- |
| **1\. Fundação** | Alta | Refinar SecurityEngine e DDM; Ativar Rate Limiting. | infra/security.py, api |
| **2\. Hardening** | Média | Integrar SAST no CI/CD; Tuning de DuckDB. | workflows/ci.yml, infra/db\_agent.py |
| **3\. Escala** | Média | Migração para IdP (Keycloak); Rotação de Segredos. | infra/security\_auth.py, Infra |
| **4\. Monitoramento** | Baixa | Dashboard de SIEM e Auditoria Centralizada. | dashboard, infra/logging.py |

