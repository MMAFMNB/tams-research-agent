# Task 15: Implement Supabase Auth and Login Page

## Status: PENDING
## Priority: high
## Dependencies: 11

## Description
Integrate Supabase Auth for user authentication with email/password login, magic link option, session management, and a TAM Liquid Glass styled login page. Include invite-only registration flow where admins send invite links.

## Details
Use supabase-py auth module. Create a login page component that renders before any app content using st.session_state for auth gating. Style with TAM Liquid Glass theme (glass cards, floating orbs background, TAM logo). Implement: login, logout, password reset, magic link, session persistence ('remember me'). Store user profile in session state after login. Create invite flow: admin generates invite link with pre-assigned role.

## Test Strategy
1. Test email/password login flow end-to-end
2. Test magic link delivery and authentication
3. Test session persistence across page reloads
4. Test password reset flow
5. Test invalid credentials handling
6. Test invite-only registration
7. Verify login page renders correctly with TAM theme

## Subtasks
No subtasks yet — run task-master expand to generate.
