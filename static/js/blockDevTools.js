// blockDevTools.js

(function() {
    let devToolsOpened = false; // 개발자 도구가 열렸는지 추적하는 변수
    let warningDisplayed = false; // 경고가 이미 표시되었는지 추적하는 변수

    // 모바일 장치 감지 함수
    function isMobileDevice() {
        return /Mobi|Android|iPhone|iPad|iPod|Windows Phone/i.test(navigator.userAgent);
    }

    // 키 입력을 막기 위한 이벤트 리스너 (모바일 장치가 아닌 경우에만 적용)
    if (!isMobileDevice()) {
        document.addEventListener('keydown', function(e) {
            const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;

            if (
                e.key === "F12" ||
                (e.ctrlKey && e.shiftKey && e.key === "I") ||
                (e.ctrlKey && e.shiftKey && e.key === "J") ||
                (e.ctrlKey && e.key === "U") ||
                (isMac && e.metaKey && e.altKey && e.key.toUpperCase() === "I") || // Cmd+Opt+I (Mac)
                (isMac && e.metaKey && e.altKey && e.key.toUpperCase() === "J") || // Cmd+Opt+J (Mac)
                (isMac && e.metaKey && e.shiftKey && e.key.toUpperCase() === "C") // Cmd+Shift+C (Mac)
            ) {
                e.preventDefault();
                alert("개발자 도구 사용이 차단되었습니다.");
            }
        });

        // 개발자 도구 열림 여부 감지 함수 (모바일 장치가 아닌 경우에만 적용)
        function detectDevTools() {
            if (devToolsOpened) return; // 이미 감지된 경우 함수 종료

            const threshold = 160; // 개발자 도구 창의 크기(threshold)
            const widthThreshold = window.outerWidth - window.innerWidth > threshold;
            const heightThreshold = window.outerHeight - window.innerHeight > threshold;

            if (widthThreshold || heightThreshold) {
                devToolsOpened = true; // 개발자 도구 열림 상태로 설정

                if (!warningDisplayed) {
                    warningDisplayed = true; // 경고가 이미 표시되었음을 설정
                    alert("개발자 도구가 열려 있습니다. 사이트 사용이 제한될 수 있습니다.");
                    
                    // 사이트를 완전히 비활성화
                    disableSite();

                    // 경고 페이지로 리디렉션
                    window.location.href = '/auth/warning';
                }
            }
        }

        // 개발자 도구 열림 여부를 감지하는 interval 설정
        setInterval(detectDevTools, 1000);
    }

    // 사이트 전체를 비활성화하는 함수
    function disableSite() {
        // 전체 사이트에 오버레이 추가
        const overlay = document.createElement('div');
        overlay.id = 'dev-tools-overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        overlay.style.color = 'white';
        overlay.style.display = 'flex';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        overlay.style.zIndex = '10000';
        overlay.innerHTML = '<h1>개발자 도구 사용이 감지되었습니다. 사이트 사용이 제한됩니다.</h1>';
        document.body.appendChild(overlay);

        // 모든 링크 및 버튼 비활성화
        const elements = document.querySelectorAll('a, button, input, textarea, select');
        elements.forEach(el => el.disabled = true);

        // 콘솔에서 지속적인 경고 출력
        setInterval(function() {
            console.clear();
            console.log('개발자 도구 사용이 감지되었습니다. 사이트 사용이 제한됩니다.');
        }, 100);
    }
})();

