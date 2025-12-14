# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - region "Notifications alt+T"
    - generic [ref=e4]:
      - generic [ref=e5]:
        - heading "Crie sua conta" [level=3] [ref=e6]
        - paragraph [ref=e7]: Acesse análises avançadas do ENEM
      - generic [ref=e9]:
        - generic [ref=e10]:
          - text: E-mail
          - textbox "E-mail" [ref=e11]:
            - /placeholder: seu@email.com
            - text: test_1765310671445@example.com
        - generic [ref=e12]:
          - text: Senha
          - textbox "Senha" [ref=e13]:
            - /placeholder: Mínimo 12 caracteres
            - text: TestPassword123!
        - generic [ref=e14]:
          - text: Confirmar Senha
          - textbox "Confirmar Senha" [ref=e15]: TestPassword123!
        - button "Cadastrar" [ref=e16] [cursor=pointer]
      - generic [ref=e18]:
        - text: Já tem uma conta?
        - link "Entrar" [ref=e19] [cursor=pointer]:
          - /url: /login
  - generic:
    - region "Notifications-top"
    - region "Notifications-top-left"
    - region "Notifications-top-right"
    - region "Notifications-bottom-left"
    - region "Notifications-bottom"
    - region "Notifications-bottom-right"
```