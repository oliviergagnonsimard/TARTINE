

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('Login');
    
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        
        userID = document.getElementById('userID').value;
        
        spawn('python', [userID])
        
    }
    
)
})

function connectToDB() {
    
}