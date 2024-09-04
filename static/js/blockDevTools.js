// blockDevTools.js

(function() {
    // F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U 키 차단
    document.onkeydown = function(e) {
        if (
            e.key === "F12" ||
            (e.ctrlKey && e.shiftKey && e.key === "I") ||
            (e.ctrlKey && e.shiftKey && e.key === "J") ||
            (e.ctrlKey && e.key === "U")
        ) {
            e.preventDefault();
            alert("개발자 도구 사용이 차단되었습니다.");
        }
    };

    // 개발자 도구 열림 여부 감지 함수
    function detectDevTools() {
        const threshold = 160; // 개발자 도구 창의 크기(threshold)
        const widthThreshold = window.outerWidth - window.innerWidth > threshold;
        const heightThreshold = window.outerHeight - window.innerHeight > threshold;

        if (widthThreshold || heightThreshold) {
            alert("개발자 도구가 열려 있습니다. 사이트 사용이 제한될 수 있습니다.");
            window.location.href = '/auth/warning'; // Flask 라우트와 일치하도록 수정
        }
    }

    // 개발자 도구 열림 여부를 감지하는 interval 설정
    setInterval(detectDevTools, 1000);

})();
