pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/tjfrhrtks12/back-testdev-0710.git'
            }
        }

        stage('Install dependencies') {
            steps {
                sh 'python3 -m pip install --upgrade pip'
                sh 'pip3 install -r requirements.txt'
            }
        }

        stage('Run Python') {
            steps {
                sh 'python3 main.py'
            }
        }
    }
}
