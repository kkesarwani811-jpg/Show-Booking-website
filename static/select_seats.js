const selectedSeats = new Set();
const ticketPrice = 250; // Dynamic based on showtime

function toggleSeat(seatElement, seatId) {
    if (selectedSeats.has(seatId)) {
        selectedSeats.delete(seatId);
        seatElement.classList.remove('selected');
    } else {
        selectedSeats.add(seatId);
        seatElement.classList.add('selected');
    }
    updateSummary();
}

function updateSummary() {
    const totalAmount = selectedSeats.size * ticketPrice;
    document.getElementById('selected-count').innerText = selectedSeats.size;
    document.getElementById('total-price').innerText = totalAmount;
}

function confirmBooking(showtimeId, userId) {
    if (selectedSeats.size === 0) {
        alert('Please select at least one seat.');
        return;
    }

    const bookingData = {
        user_id: userId,
        showtime_id: showtimeId,
        seat_ids: Array.from(selectedSeats),
        total_amount: selectedSeats.size * ticketPrice
    };

    fetch('http://127.0.0.1:5000/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bookingData)
    })
    .then(res => res.json())
    .then(data => {
        if (data.booking_id) {
            alert(`Booking Successful! ID: ${data.booking_id}`);
            window.location.href = 'index.html';
        } else {
            alert('Booking failed: ' + data.error);
        }
    });
}