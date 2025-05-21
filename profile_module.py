import streamlit as st
from datetime import datetime, timedelta

def display_profile():
    """Display the user profile with gamification stats."""
    st.subheader("👤 Your Study Profile")

    # Personalization greeting
    if st.session_state.user_name:
        st.write(f"### Hello, {st.session_state.user_name}! 👋")
    else:
        st.write("### Welcome to your Study Profile! 👋")
        with st.form("name_form"):
            user_input_name = st.text_input("What's your name?", key="name_input")
            if st.form_submit_button("Set Name"):
                if user_input_name:
                    st.session_state.user_name = user_input_name
                    st.success(f"Name set to {user_input_name}!")
                    st.rerun()
                else:
                    st.warning("Please enter a name.")
        st.markdown("---") # Add a separator if the name input is shown

    total_q_solved = st.session_state.total_questions_solved
    total_corr_ans = st.session_state.total_correct_answers
    accuracy = (total_corr_ans / total_q_solved * 100) if total_q_solved > 0 else 0

    st.markdown("---")
    st.markdown("### 📈 Overall Performance")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Questions Solved", total_q_solved)
    with col2:
        st.metric("Accuracy", f"{accuracy:.2f}%")
    with col3:
        st.metric("Current Streak", f"{st.session_state.current_streak} days 🔥")

    st.markdown("---")
    st.markdown("### 📚 Topics Covered and Performance")
    if st.session_state.topics_covered:
        # Get a sorted list of topics to display consistently
        topics_list = sorted(list(st.session_state.topics_covered))
        
        # Start a container for the tags to allow for horizontal wrapping
        st.markdown('<div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">', unsafe_allow_html=True)
        
        for topic in topics_list:
            performance = st.session_state.topic_performance.get(topic, {"total_solved": 0, "correct_solved": 0})
            total = performance["total_solved"]
            correct = performance["correct_solved"]
            
            percentage = (correct / total * 100) if total > 0 else 0

            color = "var(--text-color)" # Default for no questions solved, adapting to theme
            if total > 0:
                if percentage >= 75: # Green for great accuracy
                    color = "green"
                elif percentage >= 50: # Orange for medium accuracy (better visibility)
                    color = "orange" 
                else: # Red for bad accuracy
                    color = "red"
            
            # HTML for the compact tag
            tag_html = f"""
            <div style="
                background-color: var(--secondary-background-color); /* Matches Streamlit's secondary background */
                border-radius: 20px; /* Rounded corners like a button/tag */
                padding: 8px 15px; /* Padding inside the tag */
                display: flex;
                align-items: center; /* Vertically center content */
                font-size: 0.9em;
                color: var(--text-color);
                box-shadow: 1px 1px 3px rgba(0,0,0,0.2); /* Subtle shadow */
                min-width: 120px; /* Ensure a minimum width */
                justify-content: center; /* Center content horizontally if min-width is larger */
                margin-right: 10px; /* Spacing between tags */
                margin-bottom: 10px; /* Spacing for wrapping */
            ">
                <div style="
                    width: 12px; 
                    height: 12px; 
                    border-radius: 50%; 
                    background-color: {color}; 
                    display: inline-block; 
                    vertical-align: middle;
                    margin-right: 8px; /* Space between circle and text */
                "></div>
                <strong>{topic}</strong>: {percentage:.1f}%
            </div>
            """
            st.markdown(tag_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True) # Close the container div

    else:
        st.write("Start solving quizzes or analyzing tests to see topics you've covered!")

    st.markdown("---")
    st.markdown("### 🔖 Saved Questions")
    if st.session_state.bookmarked_questions:
        for idx, question in enumerate(st.session_state.bookmarked_questions):
            with st.expander(f"Bookmarked Question {idx+1} - {question.get('quiz_topic', 'General')}"):
                st.markdown(f"**Question:** {question['question']}")
                
                # Show answer options if available
                if 'answers' in question:
                    st.markdown("**Options:**")
                    for i, answer in enumerate(question['answers']):
                        st.write(f"{i+1}. {answer}")
                
                # Show correct answer
                if 'correctAnswer' in question:
                    st.markdown(f"**Correct Answer:** {question['answers'][question['correctAnswer']]}")
                
                # Show explanation
                if 'explanation' in question:
                    st.markdown("**Explanation:**")
                    explanation = question['explanation'].get('detailed_steps', 'No explanation available.')
                    st.markdown(explanation)
                
                # Remove bookmark button
                if st.button(f"Remove Bookmark {idx+1}", key=f"remove_bm_{idx}"):
                    st.session_state.bookmarked_questions.remove(question)
                    st.rerun()
    else:
        st.write("No questions bookmarked yet. Click the 📖 icon in quizzes to save questions here.")

    st.markdown("---")
    st.markdown("### 🔥 Quiz Streak Chart")
    st.write("🟢: Quiz completed | ⚪: No quiz")
    
    # Generate data for the streak chart (similar to GitHub's contribution graph)
    today = datetime.now().date()
    
    # Get dates for the last 365 days (a year's worth, similar to GitHub)
    num_days = 90 # Or 90 for a quarter, etc.
    dates_to_display = []
    for i in range(num_days):
        dates_to_display.append(today - timedelta(days=num_days - 1 - i))

    # Determine the number of columns (weeks) for the chart
    # A standard GitHub chart has 7 rows (days of the week)
    
    # We need to arrange `num_days` into a grid.
    # Start with the day of the week for the first date to align columns.
    first_date_in_chart = dates_to_display[0]
    first_day_of_week = first_date_in_chart.weekday() # Monday is 0, Sunday is 6

    # Prepare the grid. 7 rows for days of the week.
    # Fill in leading empty cells if the first day isn't a Monday in the chart's first column.
    chart_grid = [[] for _ in range(7)] # 7 lists for 7 days of the week (rows)

    # Add placeholders for days before the first day of the week for the first date
    for i in range(7):
        if i < first_day_of_week:
            chart_grid[i].append(" ") # Empty cell for alignment
        else:
            break # Stop filling placeholders once we hit the starting day

    for date in dates_to_display:
        day_of_week = date.weekday() # 0=Monday, 6=Sunday
        date_str = date.isoformat()
        
        symbol = "🟢" if st.session_state.streak_history.get(date_str, False) else "⚪"
        chart_grid[day_of_week].append(symbol)

    # Pad the last week's rows if they don't end on a Sunday
    max_len = max(len(row) for row in chart_grid)
    for i in range(7):
        while len(chart_grid[i]) < max_len:
            chart_grid[i].append(" ") # Pad with spaces

    # Render the chart using columns for weeks
    st.markdown("---")
    st.markdown("#### Contributions in last year")
    
    # Create a single row for the weekday labels
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Calculate number of weeks (columns)
    num_weeks = max_len
    
    # Create columns to simulate the GitHub graph
    # Add an extra column at the beginning for weekday labels
    cols = st.columns([0.5] + [1] * num_weeks) 
    
    with cols[0]: # First column for weekday labels
        st.markdown("<br>", unsafe_allow_html=True) # Spacer
        for label in weekday_labels:
            st.markdown(f"<div style='height: 40px; display: flex; align-items: center;'>{label}</div>", unsafe_allow_html=True)


    for week_idx in range(num_weeks):
        with cols[week_idx + 1]: # Shift by 1 because the first column is for labels
            # Optional: Add month label for first day of month in this column
            # This is complex to do accurately for all weeks and months
            # For simplicity, we'll omit explicit month labels for now.
            st.write(" ") # Placeholder for alignment or month

            for day_idx in range(7):
                if week_idx < len(chart_grid[day_idx]): # Ensure index is valid
                    st.markdown(f"<div style='font-size: 1.5em; text-align: center; margin: 0px;'>{chart_grid[day_idx][week_idx]}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='font-size: 1.5em; text-align: center; margin: 0px;'> </div>", unsafe_allow_html=True)

    st.markdown("---")
    st.write(f"Your longest streak: **{st.session_state.current_streak} days** (Note: this is the *current* streak, not the historical longest)")