function updateQueueData() {
    // ดึงข้อมูลจาก API หรือ Backend (สมมุติใช้ค่าตัวอย่าง)
    fetch('/api/queue') // แก้ไข URL นี้ให้ตรงกับ Flask endpoint
        .then((response) => response.json())
        .then((data) => {
            const totalCount = data.total_count;
            const currentCount = data.current_count;
            const limitAlert = data.remaining_count;

            // อัปเดต HTML
            document.getElementById('total_count').textContent = totalCount;
            document.getElementById('current_count').textContent = currentCount;
            document.getElementById('current_income').textContent = totalCount-currentCount;

            // ตรวจสอบ current_count
            const statusMessage = document.getElementById('status_message');
            if (currentCount === 0) {
                statusMessage.classList.remove('d-none');
            } else {
                statusMessage.classList.add('d-none');
            }

            // ตรวจสอบว่าเหลือประมาณ 20 คน
            const alertMessage = document.getElementById('alert_message');
            if (currentCount <= limitAlert && currentCount >1) {
                alertMessage.classList.remove('d-none');
                alertMessage.textContent = "เหลือประมาณ "+limitAlert+" คน!";
            } else {
                alertMessage.classList.add('d-none');
            }
        })
        .catch((error) => console.error('Error fetching data:', error));
}

// อัปเดตข้อมูลทุก 1 วินาที
setInterval(updateQueueData, 1000);

// ฟังก์ชันสำหรับส่งคำขอไปยัง API เพื่อเพิ่ม/ลดค่า
function updateCount(action) {
    console.log(action)
    fetch(`/api/update_queue_button`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: action }), // ส่งข้อมูล action เช่น "increment" หรือ "decrement"
    })
    .then((response) => response.json())
    .then((data) => {
        if (data.success) {
            // อัปเดตค่าปัจจุบันหลังจากเปลี่ยนแปลง
            updateQueueData();
        } else {
            console.error('Error updating count:', data.message);
        }
    })
    .catch((error) => console.error('Error:', error));
}

// เพิ่ม event listeners ให้ปุ่ม
document.getElementById('decrement_button').addEventListener('click', () => {
    updateCount('decrement');
});

document.getElementById('increment_button').addEventListener('click', () => {
    updateCount('increment');
});