# PokeAdvice 1.0 UX Product Direction

## 문서 상태

- 이 문서는 PokeAdvice 1.0의 제품/UX 방향을 정하는 기준 문서다. 특정 위젯 배치나 화면 레이아웃을 고정하는 구현 명세가 아니다.
- 아래 truth invariants는 UX 변경 시에도 지켜야 하는 권위 있는 원칙이다.
- 향후 UX 실험은 더 나은 상호작용 설계를 제안할 수 있다.
- Astra의 실험용 프로토타입은 검토할 근거이지 canonical 구현이 아니다.
- 배틀 mechanics, reducer, runtime의 계약은 각각 별도의 권위 있는 문서와 코드가 정한다.

---

## 1. 제품의 기본 목표

PokeAdvice는 사용자가 포켓몬 배틀 엔진의 내부 상태를 직접 관리하는 도구가 아니다.

사용자가 느껴야 하는 기본 경험은 다음과 같다.

> **배틀에서 일어난 일을 PokeAdvice에게 알려주고,
> 지금 무엇을 하는 것이 좋은지 조언받는다.**

사용자가 mechanics engine이 요구하는 필드를 채우는 사람처럼 느껴져서는 안 된다.

엔진은 복잡해도 괜찮다.
그러나 그 복잡성이 기본 UX에 그대로 노출되어서는 안 된다.

---

## 2. 사용자가 생각하는 실제 배틀 흐름

PokeAdvice의 UX는 포켓몬 배틀 자체의 흐름과 최대한 비슷해야 한다.

### 경기 전

시간 압박이 거의 없다.

사용자는 자신의 팀을 충분히 자세히 준비할 수 있다.

- 포켓몬 6마리
- 폼
- 기술
- 아이템
- 특성
- 성격
- 스탯 / 노력치 등 지원 가능한 build 정보

한 번 만든 팀은 **Team Library** 등에 저장하여 다시 입력하지 않고 재사용할 수 있어야 한다.

경기 전 단계는 상세해도 괜찮다.

---

## 3. 매칭 후 / 배틀 시작 전

상대 팀이 공개되면 상대 포켓몬 roster를 빠르게 입력한다.

이때 아직 턴이 시작되지 않았으므로 어느 정도 입력 시간이 있다.

기본적으로 입력해야 하는 것은:

- 상대 포켓몬 identity / form
- 필요하다면 선출 또는 lead 정보

상대의 숨겨진:

- 아이템
- 특성
- 스탯
- 세부 build

등은 확인되지 않았다면 **Unknown**이다.

메타에서 자주 쓰이는 세트는 참고 또는 hypothetical 분석에 사용할 수 있지만 현재 상대의 battle truth로 승격하지 않는다.

---

## 4. 배틀 중 핵심 loop

실제 경기 중 UX는 최대한 단순해야 한다.

기본 반복은:

```text
현재 상황 확인
→ 추천 확인
→ 기술 또는 교체
→ 실제로 일어난 일 기록
→ 다음 턴
→ 반복
```

포켓몬 게임 자체가 기본적으로 기술 또는 교체의 반복이라면, PokeAdvice가 그보다 훨씬 복잡하게 느껴져서는 안 된다.

---

## 5. State 입력보다 Event 기록

배틀 중 사용자는 가능한 한 **현재 상태값을 직접 편집하지 않는다.**

대신 실제로 본 사건을 기록한다.

예:

```text
상대가 용의춤을 사용했다
```

사용자가 직접:

```text
Attack Stage +1
Speed Stage +1
```

을 각각 입력하게 만들지 않는다.

PokeAdvice가 trusted event와 canonical mechanics로 정확하게 계산할 수 있다면 내부 상태를 스스로 갱신한다.

마찬가지로:

```text
위협 발동 확인
상대가 교체
아이템 발동
아이템 제거
상태이상 발생
HP 변화
상대가 기술 사용
```

처럼 **게임에서 관찰한 사건**을 중심으로 기록한다.

제품의 장기적인 방향은:

> **User records Events.
> PokeAdvice maintains State.**

이다.

---

## 6. 경기 중 사용자가 기본적으로 만지는 것

일반적인 턴에서 사용자가 직접 다룰 필요가 있는 정보는 대략 다음 수준이어야 한다.

- 내 기술 선택
- 내 교체 선택
- 상대가 사용한 기술
- 실제 교체
- HP 변화
- 상태이상
- 눈으로 확인한 특성/아이템 발동 또는 변화
- 필요한 경우 기타 명백한 배틀 사건

랭크 숫자, 내부 action ID, provenance, observation schema, prediction binding 같은 엔진 개념은 기본 UX에 노출하지 않는다.

잘못 기록했거나 특수한 상황에서만 **Advanced State Editor / correction surface**를 사용한다.

---

## 7. 메인 화면은 입력 폼보다 Battle View에 가깝게

PokeAdvice의 기본 화면은 데이터 입력기보다 **배틀 HUD**처럼 느껴져야 한다.

실제 포켓몬 게임이나 대회 중계 화면처럼:

- 지금 나와 있는 내 포켓몬
- 지금 나와 있는 상대 포켓몬
- HP
- 상태이상
- 중요한 랭크/필드 상태
- 팀 전체 상태
- 기술 / 교체 선택
- 추천
- 최근 또는 현재 기록

이 빠르게 읽혀야 한다.

정보량이 적어야 한다는 뜻이 아니다.

> **많은 정보를 적은 인지 비용으로 읽을 수 있어야 한다.**

---

## 8. 포켓몬 스프라이트 / 시각적 identity

가능하면 포켓몬을 이름만으로 표시하지 않고 스프라이트 또는 명확한 시각적 identity와 함께 표시한다.

활용 후보:

- team preview
- party strip
- 현재 active Pokémon
- 교체 후보
- fainted / alive 상태
- observation history

목적은 장식이 아니라 **빠른 시각적 인식**이다.

실제 공식 Pokémon asset을 공개 배포에 사용하는 문제는 UX 설계와 별도로 라이선스/배포 검토가 필요하다.

VGC 중계 화면은 **시각적 단순성과 정보 구조에 대한 참고**이며, Doubles를 1.0 scope에 추가한다는 의미는 아니다.

---

## 9. 화면 역할 분리

서로 다른 목적을 한 화면에 모두 노출하지 않는다.

### Team Library
내 팀의 지속 가능한 configuration.

### Team Preview / Battle Setup
이번 배틀의 roster와 lead 설정.

### Battle Workspace
현재 상황과 행동 추천.

### Quick Recorder
실제 일어난 사건을 빠르게 기록.

### Analysis Details
데미지, 확률, 이유, branch 등 자세한 분석.

### Advanced State Editor
실제 battle truth를 검사하거나 수정해야 할 때 사용하는 고급 도구.

### Calc Lens
“What if?”를 위한 detached hypothetical calculator.

Calc Lens의 수정은 live runtime truth에 쓰이지 않는다.

---

## 10. 반드시 유지할 Truth 원칙

UX 단순화를 위해 truth semantics를 약화시키지 않는다.

- missing = unknown
- unknown을 없음 / 0 / false / neutral / full HP 등으로 추정하지 않는다
- UI selection != observation
- considered action != executed action
- recommendation != submitted/executed action
- prediction != observation
- meta/common set != current battle truth
- historical observation != current predictive authority
- unrecorded result remains unknown
- live runtime/reducer owns battle truth
- hypothetical state never silently writes into live truth

단:

```text
trusted event/declaration
+
canonical deterministic mechanics
+
correct identity/session binding
```

으로 정확히 결정되는 사실은 rule-derived state로 자동 반영할 수 있다.

---

## 11. Unknown은 실패가 아니다

상대의 숨겨진 정보를 전부 알 수 없는 것은 정상이다.

PokeAdvice는 가능한 경우:

- 현재 알려진 정보만으로 판단하거나
- 여러 가능성을 보여주거나
- 실제 decision을 바꿀 수 있는 관찰 가능한 정보만 질문한다.

단순히 필드가 비어 있다는 이유로 사용자에게 입력을 요구하지 않는다.

---

## 12. Guided question의 기준

질문은 **엔진의 missing field collector**가 아니다.

질문할 가치가 있으려면:

1. 답에 따라 현재 판단이 실제로 달라질 수 있고,
2. 플레이어가 실제 게임에서 알 수 있는 정보여야 한다.

알 수 없는 상대 EV 등을 요구하는 식의 질문은 피한다.

`모름`은 정상적인 선택이다.

---

## 13. 경기 전 복잡성 vs 경기 중 복잡성

중요한 제품 원칙:

> **경기 전에는 자세해도 된다.
> 경기 중에는 빨라야 한다.**

내 팀 build를 경기 전에 입력하는 데 시간이 걸리는 것은 큰 문제가 아니다.

그러나 실제 턴 중에는 몇 초 안에:

```text
상황 파악
→ 선택
→ 기록
```

이 가능해야 한다.

---

## 14. 익숙한 Calculator UX를 거부하지 않는다

PokeAdvice가 독특해 보이기 위해 기존 포켓몬 계산기 UX를 일부러 피하지 않는다.

효과적인 기존 convention은 적극 사용한다.

예:

- 포켓몬 스프라이트
- 6-slot party display
- HP bar
- 4개 기술
- stage 표시
- damage range
- KO probability
- autocomplete
- saved teams
- 빠른 Pokémon/form search

목표는 새로움이 아니라 **사용성**이다.

---

## 15. Astra UX prototype의 의미

Astra experimental clone은 canonical implementation이 아니다.

그러나 다음 아이디어는 추가 검토 가치가 있다.

- compact roster + 선택한 포켓몬만 상세 표시
- live battle 중심 화면
- persistent observation controls
- hypothetical HP와 actual HP의 명확한 구분
- 중앙 workspace의 입력기 성격 감소

Astra 결과를 그대로 복사하지 않는다.

좋은 interaction만 검토하여 canonical architecture와 truth contract에 맞게 다시 구현한다.

---

## 16. 현재 1.0 UX의 핵심 문장

앞으로 UX 결정을 할 때 아래 문장을 기준으로 삼는다.

> **경기 전에는 팀을 준비한다.
> 경기 중에는 기술·교체와 실제로 일어난 일만 기록한다.
> 나머지 battle state 관리는 가능한 한 PokeAdvice가 한다.**

그리고 메인 Battle Workspace는:

> **“엔진에 무엇을 입력해야 하지?”**

가 아니라:

> **“지금 무슨 상황이고, 나는 무엇을 하면 되지?”**

에 답해야 한다.
