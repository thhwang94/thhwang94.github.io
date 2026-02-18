---
title: "Windows 11에서 WSL2 설치부터 VSCode로 WSL 프로젝트 개발까지"
date: 2026-02-16
draft: false
type: "정리"
tags: []
slug: "windows-11에서-wsl2-설치부터-vscode로-wsl-프로젝트-개발까지"
---

> 목표

  - Windows 11에서 WSL2(Ubuntu) 설치
  - Ubuntu 환경에서 프로젝트 폴더 생성
  - VSCode에서 WSL 환경으로 프로젝트 열어 개발하기


---

## 1. 왜 WSL2 + VSCode인가?

Windows에서 개발하다 보면 항상 마주치는 문제가 있다.
- Linux 서버와 로컬 환경 차이
- Windows 파일시스템에서의 개발 성능 이슈
- 가상머신은 무겁고 귀찮음
**WSL2 + VSCode** 조합은 이 문제를 거의 완벽하게 해결한다.
- Windows는 그대로 사용
- 개발은 Ubuntu에서
- VSCode는 UI만 담당, 실행은 전부 Linux
체감상 **듀얼부팅 없이 리눅스 서버 하나를 로컬에 둔 느낌**이다.
> Windows / Linux / VSCode 구조 다이어그램


---

## 2. Windows 11에서 WSL2 설치

### 2-1. 관리자 PowerShell 실행

시작 메뉴 → PowerShell → **관리자 권한으로 실행**
> 관리자 PowerShell 실행 화면

### 2-2. WSL 설치 (한 줄)

```powershell
wsl --install

```

이 명령 하나로 아래가 전부 자동 설치된다.
- WSL 기능 활성화
- Virtual Machine Platform
- WSL2 설정
- Ubuntu 설치
설치 후 **재부팅 필수**.
> wsl --install 실행 결과


---

## 3. Ubuntu 초기 설정

재부팅 후 Ubuntu가 실행되면:
- username 설정 (예: `taehwan`)
- password 설정
기본 업데이트 권장:
```bash
sudo apt update && sudo apt upgrade -y

```

WSL2인지 확인:
```powershell
wsl -l -v

```

출력 예시:
```plain text
Ubuntu   Running   2

```

> Ubuntu 초기 로그인 화면wsl -l -v 결과


---

## 4. Windows Terminal에서 Ubuntu 제대로 쓰기

> ⚠️ 중요: CMD / PowerShell ≠ Windows Terminal

Windows Terminal은 여러 쉘(PowerShell, CMD, WSL)을 관리하는 컨테이너 앱이다.
- 시작 메뉴에서 **Windows Terminal** 실행
- 없다면 Microsoft Store에서 설치
> Windows Terminal 실행 화면 (탭 UI 강조)


---

### 4-1. Ubuntu 프로필 수동 추가 (자동으로 안 생기는 경우)

설정 (`Ctrl + ,`) → Profiles → **Add new profile** → New empty profile
- **Name**
```plain text
Ubuntu (WSL)

```


- **Command line**
```plain text
wsl.exe -d Ubuntu

```


- **Starting directory**
```plain text
\\wsl$\Ubuntu\home\taehwan

```


저장 후 기본 프로필로 설정하면, 터미널을 열 때마다 바로 Ubuntu 홈으로 진입한다.
> Windows Terminal 프로필 설정 화면


---

## 5. Ubuntu에서 프로젝트 폴더 만들기

Ubuntu 터미널에서:
```bash
mkdir -p ~/projects
cd ~/projects

```

예시 프로젝트 구조:
```plain text
/home/taehwan/projects
 └── fastcampus
     └── langchain_teddy

```

Windows에 이미 프로젝트가 있다면 한 번만 복사:
```bash
cp -r "/mnt/c/Users/황태환/project/fastcampus/langchain_teddy" ~/projects/fastcampus/

```

> /mnt/c는 참고/복사만, 개발은 반드시 /home 아래에서.

> /mnt/c와 /home 경로 비교 화면


---

## 6. VSCode에서 WSL 프로젝트 열기 (핵심)

### 6-1. 필수 확장 설치

Windows에 설치된 VSCode에서:
- **Remote - WSL** 확장 설치
> VSCode Extension 마켓에서 Remote-WSL 설치


---

### 6-2. WSL에서 처음 한 번 연결하기

Ubuntu 터미널에서:
```bash
cd ~/projects/fastcampus/langchain_teddy
code .

```

처음 실행 시:
- VSCode Server가 WSL 내부에 자동 설치
- VSCode가 WSL 모드로 재연결됨
좌하단에 다음 표시가 나오면 성공:
```plain text
WSL: Ubuntu

```

> VSCode 좌하단 WSL: Ubuntu 표시


---

## 7. 이제부터의 실전 사용법 (중요)

### ❌ 매번 하지 않아도 되는 것

- 매번 `wsl` 접속
- 매번 `cd` 후 `code .`
### ✅ 평소 사용 루틴

1. VSCode 실행
1. **Recent → langchain_teddy 선택**
1. 바로 개발 시작
또는:
- File → Open Folder → `/home/taehwan/projects/...`
VSCode가 자동으로 WSL에 연결된다.
> VSCode Recent Projects 화면


---

## 8. 실수했을 때 복구 방법

Windows 폴더(`C:\Users\...`)를 실수로 열었다면:
- 좌하단 `><` 클릭
- **Reopen Folder in WSL** 선택
같은 프로젝트를 WSL 환경으로 다시 연다.
> Reopen Folder in WSL 메뉴


---

## 9. 정상 동작 체크리스트

VSCode 터미널에서:
```bash
pwd
whoami

```

출력:
```plain text
/home/taehwan/projects/fastcampus/langchain_teddy
taehwan

```

좌하단:
```plain text
WSL: Ubuntu

```

이면 완벽한 상태.

---

## 10. 마무리

이 구성의 핵심은 단순하다.
- **Windows는 UI와 일상용**
- **Ubuntu(WSL)는 개발 백엔드**
- **VSCode는 연결자**
한 번만 구조를 잡아두면:
- 듀얼부팅 불필요
- VM 관리 불필요
- 서버와 로컬 환경 차이 최소화
> Windows에서 가장 현실적인 리눅스 개발 환경.


---

### 다음 단계 추천

- Python venv / conda 세팅
- Git SSH 키 (WSL 기준)
- 맥북에서 이 WSL로 SSH 접속
이제부터는 **환경이 아니라 코드에만 집중하면 된다**.
